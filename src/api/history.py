"""Conversation history retrieval endpoints."""

from flask import Blueprint, request, jsonify

from src.utils.openai_formatter import format_error_response
from src.api.chat import get_conversation_service

# Blueprint for history-related endpoints
history_bp = Blueprint("history", __name__)


@history_bp.route("/debug/conversations", methods=["GET"])
def debug_conversations():
    """Debug endpoint to dump all conversation data."""
    conversation_service = get_conversation_service()

    with conversation_service._lock:
        conversations_data = []
        for conv_id, conv in conversation_service._conversations.items():
            messages = conversation_service._messages.get(conv_id, [])
            conversations_data.append({
                "conversation_id": conv_id,
                "image_id": conv.image_id,
                "session_id": conv.session_id,
                "created_at": conv.created_at.isoformat(),
                "last_activity": conv.last_activity.isoformat(),
                "message_count": len(messages),
                "messages": [
                    {
                        "message_id": msg.message_id,
                        "role": msg.role,
                        "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
                        "token_count": msg.token_count
                    }
                    for msg in messages
                ]
            })

        return jsonify({
            "total_conversations": len(conversations_data),
            "conversations": conversations_data
        }), 200


@history_bp.route("/history", methods=["GET"])
def get_history():
    """Retrieve conversation history filtered by image_id, session_id, or both.

    Implements: User Story 3 (View and Navigate Conversation History)

    Query Parameters:
        - image_id (optional): Filter conversations by image ID
        - session_id (optional): Filter conversations by session ID
        - limit (optional, default=20, max=100): Max conversations to return

    Returns:
        200: HistoryResponse with conversations and messages
        400: Missing required filter parameters (at least one of image_id or session_id)
        500: Internal server error
    """
    # Get query parameters
    image_id = request.args.get("image_id", None)
    session_id = request.args.get("session_id", None)
    limit = request.args.get("limit", 20, type=int)

    # Validate at least one filter provided
    if not image_id and not session_id:
        return jsonify(
            format_error_response(
                message="At least one of image_id or session_id is required",
                error_type="invalid_request_error",
                param=None,
                code="missing_filter",
            )
        ), 400

    # Validate limit range
    if limit < 1 or limit > 100:
        return jsonify(
            format_error_response(
                message="Limit must be between 1 and 100",
                error_type="invalid_request_error",
                param="limit",
                code="invalid_limit",
            )
        ), 400

    # Retrieve conversations from service
    conversation_service = get_conversation_service()
    conversations = []

    try:
        # Retrieve by image_id
        if image_id:
            conversations.extend(conversation_service.get_conversations_by_image(image_id))

        # Retrieve by session_id (if also provided, merge results)
        if session_id:
            session_conversations = conversation_service.get_conversations_by_session(
                session_id
            )

            # If both filters provided, find intersection (conversations matching BOTH)
            if image_id:
                # Filter to only conversations that match both image_id AND session_id
                session_conversation_ids = {c.conversation_id for c in session_conversations}
                conversations = [
                    c for c in conversations if c.conversation_id in session_conversation_ids
                ]
            else:
                conversations.extend(session_conversations)

        # Remove duplicates (if any)
        seen = set()
        unique_conversations = []
        for conv in conversations:
            if conv.conversation_id not in seen:
                seen.add(conv.conversation_id)
                unique_conversations.append(conv)
        conversations = unique_conversations

        # Sort by last_activity descending (most recent first)
        conversations.sort(key=lambda c: c.last_activity, reverse=True)

        # Apply limit
        conversations = conversations[:limit]

        # Build response payload
        response_conversations = []
        for conv in conversations:
            # Get messages for this conversation
            messages = conversation_service.get_messages(conv.conversation_id)

            # Format conversation with messages
            response_conversations.append(
                {
                    "conversation_id": conv.conversation_id,
                    "image_id": conv.image_id,
                    "session_id": conv.session_id,
                    "created_at": conv.created_at.isoformat() + "Z",
                    "last_activity": conv.last_activity.isoformat() + "Z",
                    "messages": [
                        {
                            "message_id": msg.message_id,
                            "role": msg.role,
                            "content": msg.content,
                            "created_at": msg.created_at.isoformat() + "Z",
                            "token_count": msg.token_count,
                        }
                        for msg in messages
                    ],
                }
            )

        return jsonify(
            {
                "conversations": response_conversations,
                "count": len(response_conversations),
            }
        ), 200

    except Exception as e:
        # Log error but return generic error to client
        from src.utils.logger import get_logger

        logger = get_logger(__name__)
        logger.error(f"Failed to retrieve conversation history: {e}", exc_info=True)

        return jsonify(
            format_error_response(
                message="An error occurred while retrieving conversation history",
                error_type="api_error",
                code="history_retrieval_failed",
            )
        ), 500
