"""Chat API endpoints."""

import threading
import uuid
from flask import Blueprint, request, jsonify, current_app, make_response, Response

from src.models.chat import ChatRequest
from src.services.session_service import SessionService
from src.services.chat_service import ChatService
from src.services.mock_openai_service import mock_openai_chat
from src.utils.openai_formatter import format_error_response, format_silly_excuse, format_photo_relevance_prompt
from src.utils.security import validate_prompt
from src.api.middleware import limiter, get_session_id

# Blueprint for chat-related endpoints
chat_bp = Blueprint("chat", __name__)

# Streaming connection limiter — initialized lazily with config value
_stream_semaphore = None
_stream_semaphore_lock = threading.Lock()


def get_stream_semaphore():
    """Get or create the BoundedSemaphore for streaming connection limiting."""
    global _stream_semaphore
    if _stream_semaphore is None:
        with _stream_semaphore_lock:
            if _stream_semaphore is None:
                max_connections = current_app.config.get("MAX_STREAMING_CONNECTIONS", 50)
                _stream_semaphore = threading.BoundedSemaphore(max_connections)
    return _stream_semaphore

# Global services (initialized on first request)
_session_service = None
_chat_service = None
_conversation_service = None


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


def get_conversation_service():
    """Get or create conversation service instance."""
    global _conversation_service
    if _conversation_service is None:
        from src.services.conversation_service import ConversationService

        _conversation_service = ConversationService()
    return _conversation_service


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

    # Resolve which image to use (None is OK for text-only chat)
    image_id, _ = chat_service.resolve_image_id(session, explicit_image_id)

    # If image exists, check if upload is in progress
    if image_id and chat_service.check_upload_in_progress(image_id):
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
    conversation_service = get_conversation_service()

    # Get or create conversation for this image/session (T009)
    conversation = conversation_service.get_or_create_conversation(
        image_id=image_id, session_id=session.session_id
    )

    # Retrieve conversation history for AI context
    history = conversation_service.get_context_for_ai(
        conversation.conversation_id,
        max_messages=current_app.config.get("HISTORY_MAX_MESSAGES", 50),
        max_tokens=current_app.config.get("HISTORY_MAX_TOKENS", 10_000),
    )

    # Add user message to history (graceful degradation per FR-012)
    conversation_service.add_message(
        conversation.conversation_id, role="user", content=prompt
    )
    current_app.logger.info(f"Added user message to conversation {conversation.conversation_id}")

    # Generate response with history context
    chat_delay = current_app.config.get("MOCK_CHAT_DELAY", 0.2)
    chat_response = chat_service.chat(
        prompt=prompt, image_id=image_id, history=history, delay=chat_delay
    )

    # Add assistant response to history (graceful degradation)
    if chat_response and "choices" in chat_response:
        assistant_content = chat_response["choices"][0]["message"]["content"]
        conversation_service.add_message(
            conversation.conversation_id, role="assistant", content=assistant_content
        )
        current_app.logger.info(f"Added assistant message to conversation {conversation.conversation_id}: {assistant_content[:50]}...")
    else:
        current_app.logger.warning(f"No assistant response to save for conversation {conversation.conversation_id}")

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


@chat_bp.route("/chat/stream", methods=["POST"])
@limiter.limit(
    lambda: current_app.config["CHAT_RATE_LIMIT"],
    key_func=get_session_id,
)
def chat_stream():
    """Stream a chat response using Server-Sent Events.

    Implements: Question 2 - Streaming Responses

    Expected JSON body:
        {
            "prompt": "What do you see?",
            "image_id": "uuid"  // Optional override
        }

    Returns:
        200: SSE stream (text/event-stream)
        400: Invalid request (JSON error)
        429: Rate limit exceeded
    """
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

    # Resolve image
    image_id, _ = chat_service.resolve_image_id(session, explicit_image_id)

    # If upload in progress, return JSON error (can't stream a silly excuse)
    if image_id and chat_service.check_upload_in_progress(image_id):
        return jsonify(
            format_error_response(
                message="Image upload in progress. Please try again shortly.",
                error_type="invalid_request_error",
                code="upload_in_progress",
            )
        ), 202

    # Check concurrent connection limit (non-blocking acquire)
    semaphore = get_stream_semaphore()
    if not semaphore.acquire(blocking=False):
        return jsonify(
            format_error_response(
                message="Too many active streaming connections. Please try again shortly.",
                error_type="api_error",
                code="streaming_capacity_exceeded",
            )
        ), 503

    conversation_service = get_conversation_service()

    # Get or create conversation for this image/session (T010)
    conversation = conversation_service.get_or_create_conversation(
        image_id=image_id, session_id=session.session_id
    )

    # Retrieve conversation history for AI context
    history = conversation_service.get_context_for_ai(
        conversation.conversation_id,
        max_messages=current_app.config.get("HISTORY_MAX_MESSAGES", 50),
        max_tokens=current_app.config.get("HISTORY_MAX_TOKENS", 10_000),
    )

    # Add user message to history (graceful degradation per FR-012)
    conversation_service.add_message(
        conversation.conversation_id, role="user", content=prompt
    )
    current_app.logger.info(f"[STREAM] Added user message to conversation {conversation.conversation_id}")

    chat_delay = current_app.config.get("MOCK_CHAT_DELAY", 0.2)
    stream_timeout = current_app.config.get("STREAM_TIMEOUT_SECONDS", 30)

    # Get the streaming generator with history context
    inner_gen = chat_service.stream_chat(
        prompt=prompt,
        image_id=image_id,
        history=history,
        delay=chat_delay,
        timeout_seconds=stream_timeout,
    )

    # Capture streamed content to add to history after completion
    streamed_chunks = []
    full_content_parts = []  # Reconstruct full content from deltas

    # Priority 2: Reconnection support
    # Check for Last-Event-ID header (SSE reconnection standard)
    last_event_id = request.headers.get('Last-Event-ID')
    skip_until_event = None

    if last_event_id:
        # Client is reconnecting - they want to resume from this event
        # Format: "conv-{conversation_id}-{event_number}"
        try:
            parts = last_event_id.split('-')
            if len(parts) >= 3 and parts[0] == 'conv':
                skip_until_event = int(parts[-1])
        except (ValueError, IndexError):
            pass  # Invalid format, start from beginning

    def guarded_stream():
        """Wrapper that releases semaphore, captures content, handles backpressure, and supports reconnection."""
        import time
        import json
        from src.utils.logger import setup_logger

        logger = setup_logger(__name__)
        buffer_size = 0
        max_buffer_size = 10  # Maximum chunks to buffer before slowing down
        event_counter = 0  # Track event IDs for reconnection

        try:
            for chunk in inner_gen:
                event_counter += 1

                # Priority 2: Skip events if reconnecting from a specific point
                if skip_until_event is not None and event_counter <= skip_until_event:
                    continue  # Skip already-sent events

                # Generate unique event ID for this chunk (Priority 2)
                event_id = f"conv-{conversation.conversation_id}-{event_counter}"

                # Debug: Log first few chunks to see format
                if event_counter <= 3:
                    logger.info(f"[STREAM] Chunk {event_counter}: {chunk[:200]}")

                # Capture content chunks for history
                # Note: JSON has space after colon: "content": "text" not "content":"text"
                if '"delta":' in chunk and '"content":' in chunk:
                    streamed_chunks.append(chunk)
                    logger.info(f"[STREAM] Captured chunk {event_counter} for history")

                    # Reconstruct full content from delta chunks (Priority 3 fix)
                    try:
                        # Parse SSE data line to extract content
                        if chunk.startswith('data: '):
                            json_str = chunk[6:].strip()
                            if json_str and json_str != '[DONE]':
                                data = json.loads(json_str)
                                content = data.get('choices', [{}])[0].get('delta', {}).get('content')
                                if content:
                                    full_content_parts.append(content)
                    except (json.JSONDecodeError, KeyError):
                        pass  # Skip malformed chunks

                # Backpressure handling (Priority 1 fix)
                buffer_size += 1
                if buffer_size > max_buffer_size:
                    # Slow consumer detected - add small delay to prevent overwhelming
                    time.sleep(0.01)  # 10ms backpressure delay
                    buffer_size = max(0, buffer_size - 2)  # Reduce buffer assumption

                # Priority 2: Prepend event ID to SSE chunk (SSE standard format)
                # SSE format: "id: <event-id>\ndata: <payload>\n\n"
                if chunk.startswith('data: '):
                    # Add event ID before data line
                    yield f"id: {event_id}\n"

                yield chunk

        finally:
            # Add assistant response to history after stream completes
            # Use reconstructed content (Priority 3 fix)
            logger.info(f"[STREAM] Finalizing stream. full_content_parts count: {len(full_content_parts)}, streamed_chunks count: {len(streamed_chunks)}")

            if full_content_parts:
                full_content = ''.join(full_content_parts)
                logger.info(f"[STREAM] Adding assistant message from full_content_parts: {full_content[:100]}...")
                conversation_service.add_message(
                    conversation.conversation_id,
                    role="assistant",
                    content=full_content,
                )
            elif streamed_chunks:
                # Fallback if content reconstruction failed
                logger.warning(f"[STREAM] Content reconstruction failed, using placeholder")
                conversation_service.add_message(
                    conversation.conversation_id,
                    role="assistant",
                    content="[Streamed response - content reconstruction failed]",
                )
            else:
                logger.error(f"[STREAM] No content to save! Both full_content_parts and streamed_chunks are empty")
            semaphore.release()

    # Update session
    session_service.update_session(session)

    # Return SSE stream
    return Response(
        guarded_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Connection": "keep-alive",
        },
    )


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
