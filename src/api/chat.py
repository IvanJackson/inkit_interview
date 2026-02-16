"""Chat API endpoints."""

import uuid
from flask import Blueprint, request, jsonify, current_app, make_response

from src.models.chat import ChatRequest
from src.services.session_service import SessionService
from src.services.chat_service import ChatService
from src.services.mock_openai_service import mock_openai_chat
from src.utils.openai_formatter import format_error_response, format_silly_excuse, format_photo_relevance_prompt
from src.utils.security import validate_prompt
from src.api.middleware import limiter, get_session_id

# Blueprint for chat-related endpoints
chat_bp = Blueprint("chat", __name__)

# Global services (initialized on first request)
_session_service = None
_chat_service = None


def get_session_service():
    """Get or create session service instance."""
    global _session_service
    if _session_service is None:
        _session_service = SessionService(
            session_timeout_hours=current_app.config["SESSION_TIMEOUT_HOURS"]
        )
    return _session_service


def get_chat_service():
    """Get or create chat service instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService(
            silly_excuses=current_app.config["SILLY_EXCUSES"]
        )
    return _chat_service


def get_or_create_session_from_request():
    """Extract or create session from request headers/cookies."""
    session_service = get_session_service()

    # Get session ID from cookie
    session_id = request.cookies.get(current_app.config["SESSION_COOKIE_NAME"])

    # Generate browser device ID from headers
    user_agent = request.headers.get("User-Agent", "")
    accept_language = request.headers.get("Accept-Language", "")
    remote_addr = request.remote_addr or ""

    browser_device_id = session_service.generate_browser_device_id(
        user_agent, accept_language, remote_addr
    )

    # Get or create session
    session = session_service.get_or_create_session(session_id, browser_device_id)

    return session


@chat_bp.route("/chat", methods=["POST"])
@limiter.limit(
    lambda: current_app.config["CHAT_RATE_LIMIT"],
    key_func=get_session_id,
)
def chat():
    """Chat about an uploaded image.

    Implements: FR-016 through FR-032

    Expected JSON body:
        {
            "prompt": "What do you see?",
            "image_id": "uuid"  // Optional override
        }

    Returns:
        200: Chat completion response
        202: Request queued (silly excuse)
        400: Invalid request
        404: No image available
        429: Rate limit exceeded
    """
    # Get or create session
    session = get_or_create_session_from_request()
    session_service = get_session_service()
    chat_service = get_chat_service()

    # Parse request data
    data = request.get_json()
    if not data or "prompt" not in data:
        return jsonify(
            format_error_response(
                message="Missing required field: prompt",
                error_type="invalid_request_error",
                code="missing_prompt",
            )
        ), 400

    prompt = data["prompt"]
    explicit_image_id = data.get("image_id")

    # Validate and sanitize prompt
    try:
        prompt = validate_prompt(prompt, max_length=current_app.config["MAX_PROMPT_LENGTH"])
    except ValueError as e:
        return jsonify(
            format_error_response(
                message=str(e),
                error_type="invalid_request_error",
                param="prompt",
                code="invalid_prompt",
            )
        ), 400

    # Resolve which image to use
    image_id, error = chat_service.resolve_image_id(session, explicit_image_id)

    if error:
        return jsonify(
            format_error_response(
                message=error,
                error_type="invalid_request_error",
                code="no_image",
            )
        ), 404

    # Check if upload is in progress
    if chat_service.check_upload_in_progress(image_id):
        # Generate silly excuse
        excuse = chat_service.generate_silly_excuse()

        # Create chat request
        chat_request = ChatRequest(
            id=str(uuid.uuid4()),
            session_id=session.session_id,
            prompt=prompt,
            image_id=image_id,
            queue_status="queued",
        )

        # Queue the request
        queue_id = chat_service.queue_request(chat_request, image_id)

        # Return silly excuse with queue ID
        response = make_response(jsonify(format_silly_excuse(excuse)), 202)
        response.headers["X-Queue-ID"] = queue_id
        response.headers["X-Queue-Poll-URL"] = f"/chat/queue/{queue_id}"

        # Set session cookie
        response.set_cookie(
            current_app.config["SESSION_COOKIE_NAME"],
            session.session_id,
            max_age=session_service.session_timeout_hours * 3600,
        )

        return response

    # Normal flow - process chat request immediately
    chat_delay = current_app.config.get("MOCK_CHAT_DELAY",0.2)
    chat_response = mock_openai_chat(prompt, image_id, delay=chat_delay)

    # Update session
    session_service.update_session(session)

    # Return response with session cookie
    response = make_response(jsonify(chat_response), 200)
    response.set_cookie(
        current_app.config["SESSION_COOKIE_NAME"],
        session.session_id,
        max_age=session_service.session_timeout_hours * 3600,
    )

    return response


@chat_bp.route("/chat/relevance", methods=["POST"])
def chat_relevance():
    """Handle photo relevance confirmation.

    Implements: FR-028 through FR-030

    Expected JSON body:
        {
            "action": "start_new" | "keep_current",
            "new_image_id": "uuid"  // Required if start_new
        }

    Returns:
        200: Confirmation processed
        400: Invalid request
    """
    # Get session
    session = get_or_create_session_from_request()
    session_service = get_session_service()

    # Parse request data
    data = request.get_json()
    if not data or "action" not in data:
        return jsonify(
            format_error_response(
                message="Missing required field: action",
                error_type="invalid_request_error",
                code="missing_action",
            )
        ), 400

    action = data["action"]

    if action not in ["start_new", "keep_current"]:
        return jsonify(
            format_error_response(
                message="Invalid action. Must be 'start_new' or 'keep_current'",
                error_type="invalid_request_error",
                param="action",
                code="invalid_action",
            )
        ), 400

    if action == "start_new":
        new_image_id = data.get("new_image_id")
        if not new_image_id:
            return jsonify(
                format_error_response(
                    message="Missing required field: new_image_id",
                    error_type="invalid_request_error",
                    code="missing_image_id",
                )
            ), 400

        # Update session to new image
        session.current_image_id = new_image_id
        session.conversation_topic = None  # Reset topic

        message = "Started new conversation with the new image"

    else:  # keep_current
        message = "Continuing with current image"

    # Update session
    session_service.update_session(session)

    # Return confirmation
    response = make_response(jsonify({"message": message}), 200)
    response.set_cookie(
        current_app.config["SESSION_COOKIE_NAME"],
        session.session_id,
        max_age=session_service.session_timeout_hours * 3600,
    )

    return response


@chat_bp.route("/session/restore", methods=["POST"])
def restore_session_endpoint():
    """Restore an expired session.

    Implements: FR-034 through FR-037

    Expected JSON body:
        {
            "session_id": "uuid",
            "auth_token": "optional"  // For device validation
        }

    Returns:
        200: Session restored
        400: Invalid request
        404: Session not found or device mismatch
    """
    session_service = get_session_service()

    # Parse request data
    data = request.get_json()
    if not data or "session_id" not in data:
        return jsonify(
            format_error_response(
                message="Missing required field: session_id",
                error_type="invalid_request_error",
                code="missing_session_id",
            )
        ), 400

    session_id = data["session_id"]

    # Generate browser device ID from headers
    user_agent = request.headers.get("User-Agent", "")
    accept_language = request.headers.get("Accept-Language", "")
    remote_addr = request.remote_addr or ""

    browser_device_id = session_service.generate_browser_device_id(
        user_agent, accept_language, remote_addr
    )

    # Attempt to restore session
    restored_session = session_service.restore_session(session_id, browser_device_id)

    if not restored_session:
        return jsonify(
            format_error_response(
                message="Session not found or device mismatch. Please re-authenticate.",
                error_type="invalid_request_error",
                code="session_not_found",
            )
        ), 404

    # Return restored session context
    response = make_response(jsonify({
        "message": "Session restored successfully",
        "session_id": restored_session.session_id,
        "current_image_id": restored_session.current_image_id,
        "conversation_topic": restored_session.conversation_topic,
    }), 200)

    response.set_cookie(
        current_app.config["SESSION_COOKIE_NAME"],
        restored_session.session_id,
        max_age=session_service.session_timeout_hours * 3600,
    )

    return response


@chat_bp.route("/chat/queue/<queue_id>", methods=["GET"])
def poll_queue(queue_id):
    """Poll for queued request result.

    Implements: FR-024a through FR-024d

    Returns:
        200: Request completed (includes response)
        202: Request still pending
        404: Queue ID not found
    """
    chat_service = get_chat_service()

    # Get queued request
    queued_request = chat_service.get_queued_request(queue_id)

    if not queued_request:
        return jsonify(
            format_error_response(
                message="Queue ID not found",
                error_type="invalid_request_error",
                code="queue_not_found",
            )
        ), 404

    # Check if completed
    if queued_request.is_completed():
        return jsonify(queued_request.response), 200

    # Still pending
    return jsonify({
        "status": "pending",
        "message": "Request is being processed. Please try again shortly.",
    }), 202
