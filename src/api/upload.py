"""Upload API endpoints."""

from flask import Blueprint, request, jsonify, current_app, make_response, send_file

from src.services.image_service import ImageService
from src.services.mock_openai_service import mock_openai_vision_analysis, mock_openai_chat
from src.utils.openai_formatter import format_error_response
from src.api.middleware import limiter, get_session_id

# Blueprint for upload-related endpoints
upload_bp = Blueprint("upload", __name__)

# Global image service (initialized on first request)
_image_service = None


def get_image_service():
    """Get or create image service instance."""
    global _image_service
    if _image_service is None: 
        _image_service = ImageService(
            upload_folder=current_app.config["UPLOAD_FOLDER"],
            max_size_bytes=current_app.config["MAX_CONTENT_LENGTH"],
            max_width=current_app.config["MAX_IMAGE_WIDTH"],
            max_height=current_app.config["MAX_IMAGE_HEIGHT"],
        )
    return _image_service


def get_session_and_services_from_request():
    """Get session and services from request (avoid circular import)."""
    from src.api.chat import (
        get_session_service,
        get_chat_service,
        get_conversation_service,
        get_or_create_session_from_request,
    )

    session = get_or_create_session_from_request()
    session_service = get_session_service()
    chat_service = get_chat_service()
    conversation_service = get_conversation_service()

    return session, session_service, chat_service, conversation_service


@upload_bp.route("/upload", methods=["POST"])
@limiter.limit(
    lambda: current_app.config["UPLOAD_RATE_LIMIT"],
    key_func=get_session_id,
)
def upload_image():
    """Upload an image file for analysis with optional prompt.

    Implements: FR-001 through FR-015

    Accepts:
        - image (file, required): Image file to upload
        - prompt (string, optional): Optional question about the image

    If prompt is provided, returns both vision analysis AND chat response.
    If no prompt, returns only vision analysis (user can chat later).

    Returns:
        200: Success with image_id, vision analysis, and optional chat response
        400: Bad request (missing file)
        413: File too large
        415: Unsupported file type
        422: Validation failed or corruption detected
        429: Rate limit exceeded
    """
    # Check if file is present
    if "image" not in request.files:
        return jsonify(
            format_error_response(
                message="No image file provided",
                error_type="invalid_request_error",
                param="image",
                code="missing_file",
            )
        ), 400

    file = request.files["image"]

    # Check if filename is empty
    if file.filename == "":
        return jsonify(
            format_error_response(
                message="No image file selected",
                error_type="invalid_request_error",
                param="image",
                code="empty_filename",
            )
        ), 400

    # Process upload
    image_service = get_image_service()
    image, error = image_service.process_upload(file, file.filename)

    if error:
        error_code = error.get("code", "unknown")

        # Handle corruption case specially
        if error_code == "corruption_suspected":
            corrupted_image = error.get("corrupted_image")
            return jsonify({
                "error": {
                    "message": "Image appears corrupted. Please confirm if you want to proceed.",
                    "type": "validation_error",
                    "code": "corruption_suspected",
                },
                "image_id": error.get("image_id"),
                "preview_base64": error.get("preview_base64"),
                "confirmation_url": "/upload/confirm",
            }), 422

        # Handle other errors
        status_code_map = {
            "unsupported_format": 415,
            "image_too_large": 413,
            "validation_failed": 422,
        }

        status_code = status_code_map.get(error_code, 400)

        return jsonify(
            format_error_response(
                message=error.get("error", "Validation failed"),
                error_type="invalid_request_error",
                param="image",
                code=error_code,
            )
        ), status_code

    # Success - run vision analysis
    vision_delay = current_app.config.get("MOCK_VISION_DELAY", 0.1)
    vision_result = mock_openai_vision_analysis(image.file_path, delay=vision_delay)

    # Store vision analysis in image (Responses API format: output[0].content[0].text)
    image.vision_analysis = vision_result["output"][0]["content"][0]["text"]

    # Get session and update with current image
    session, session_service, chat_service, conversation_service = (
        get_session_and_services_from_request()
    )
    session.current_image_id = image.id
    session_service.update_session(session)

    # Create conversation for this image (T008)
    conversation = conversation_service.get_or_create_conversation(
        image_id=image.id, session_id=session.session_id
    )

    # Process any queued requests for this image
    def process_chat_callback(chat_request):
        """Process a queued chat request."""
        chat_delay = current_app.config.get("MOCK_CHAT_DELAY", 0.2)
        return mock_openai_chat(chat_request.prompt, chat_request.image_id, delay=chat_delay)

    chat_service.process_queued_requests(image.id, process_chat_callback)

    # Check for optional prompt (hybrid approach)
    prompt = request.form.get("prompt", None) or request.form.get("question", None)
    chat_response = None

    if prompt:
        # User provided a prompt - generate chat response immediately
        from src.utils.security import validate_prompt

        try:
            # Validate the prompt
            validated_prompt = validate_prompt(prompt)

            # Generate chat response
            chat_delay = current_app.config.get("MOCK_CHAT_DELAY", 0.2)
            chat_response = mock_openai_chat(validated_prompt, image.id, delay=chat_delay)
        except ValueError:
            # If prompt validation fails, still return the upload success
            # but skip the chat response (user can chat later with valid prompt)
            pass

    # Build response payload
    response_payload = {
        "image_id": image.id,
        "filename": image.filename,
        "size_bytes": image.size_bytes,
        "width": image.width,
        "height": image.height,
        "format": image.format,
        "uploaded_at": image.uploaded_at.isoformat(),
        "analysis": vision_result,
    }

    # Add chat response if prompt was provided
    if chat_response:
        response_payload["chat_response"] = chat_response

    # Return success response with session cookie
    response = make_response(jsonify(response_payload), 200)

    response.set_cookie(
        current_app.config["SESSION_COOKIE_NAME"],
        session.session_id,
        max_age=session_service.session_timeout_hours * 3600,
    )

    return response


@upload_bp.route("/upload/confirm", methods=["POST"])
def confirm_upload():
    """Confirm upload of a potentially corrupted image.

    Implements: FR-008, FR-009

    Expected JSON body:
        {
            "image_id": "uuid",
            "action": "confirm_valid" | "confirm_corrupted"
        }

    Returns:
        200: Confirmation processed
        400: Invalid request
        404: Image not found
    """
    data = request.get_json()

    if not data or "image_id" not in data or "action" not in data:
        return jsonify(
            format_error_response(
                message="Missing required fields: image_id and action",
                error_type="invalid_request_error",
                code="missing_fields",
            )
        ), 400

    image_id = data["image_id"]
    action = data["action"]

    if action not in ["confirm_valid", "confirm_corrupted"]:
        return jsonify(
            format_error_response(
                message="Invalid action. Must be 'confirm_valid' or 'confirm_corrupted'",
                error_type="invalid_request_error",
                param="action",
                code="invalid_action",
            )
        ), 400

    image_service = get_image_service()
    image = image_service.get_image(image_id)

    if not image:
        return jsonify(
            format_error_response(
                message="Image not found",
                error_type="invalid_request_error",
                code="not_found",
            )
        ), 404

    if action == "confirm_valid":
        # User confirms image is valid - run vision analysis
        vision_delay = current_app.config.get("MOCK_VISION_DELAY", 0.1)
        vision_result = mock_openai_vision_analysis(image.file_path, delay=vision_delay)

        image.corruption_status = "valid"
        image.vision_analysis = vision_result["output"][0]["content"][0]["text"]

        return jsonify({
            "message": "Image confirmed as valid",
            "image_id": image.id,
            "analysis": vision_result,
        }), 200

    else:  # confirm_corrupted
        image.corruption_status = "confirmed"

        return jsonify({
            "message": "Image confirmed as corrupted. Please upload a new image.",
            "suggested_action": "re-upload",
        }), 200


@upload_bp.route("/images/<image_id>", methods=["GET"])
def get_image(image_id):
    """Retrieve an uploaded image by ID.

    Args:
        image_id: UUID of the image

    Returns:
        200: Image file
        404: Image not found
    """
    image_service = get_image_service()
    image = image_service.get_image(image_id)

    if not image:
        return jsonify(
            format_error_response(
                message="Image not found",
                error_type="invalid_request_error",
                code="not_found",
            )
        ), 404

    # Return the image file
    try:
        return send_file(
            image.file_path,
            mimetype=f'image/{image.format.lower()}',
            as_attachment=False,
            download_name=image.filename
        )
    except FileNotFoundError:
        return jsonify(
            format_error_response(
                message="Image file not found on server",
                error_type="api_error",
                code="file_not_found",
            )
        ), 404
