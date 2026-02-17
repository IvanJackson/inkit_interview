"""Thread-safe conversation history storage and retrieval service."""

import threading
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from src.models.conversation import Conversation
from src.models.message import Message
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ConversationService:
    """Manages conversation history with thread-safe in-memory storage.

    Storage uses nested dictionaries protected by threading.RLock, matching
    the SessionService pattern from Q1/Q2. Provides conversation creation,
    message storage, and context retrieval with truncation for AI prompts.
    """

    def __init__(self):
        """Initialize conversation service with empty storage and thread lock."""
        # Primary storage
        self._conversations: Dict[str, Conversation] = {}
        self._messages: Dict[str, List[Message]] = defaultdict(list)

        # Lookup indexes for efficient queries
        self._conversations_by_image: Dict[str, List[str]] = defaultdict(list)
        self._conversations_by_session: Dict[str, List[str]] = defaultdict(list)

        # Thread safety - matches SessionService pattern
        self._lock = threading.RLock()

        logger.info("ConversationService initialized with thread-safe storage")

    def get_or_create_conversation(
        self, image_id: Optional[str], session_id: str
    ) -> Conversation:
        """Get existing conversation or create new one for image/session pair.

        Uses image_id as primary lookup key (per Decision 4 in research.md).
        This enables conversation continuity across session changes - users
        can continue discussing the same image even after session expiration.

        Args:
            image_id: Image being discussed (None for text-only conversations)
            session_id: Current session ID

        Returns:
            Conversation object (existing or newly created)
        """
        try:
            with self._lock:
                # Lookup strategy: Find conversation by image_id first
                if image_id and image_id in self._conversations_by_image:
                    conversation_ids = self._conversations_by_image[image_id]
                    if conversation_ids:
                        # Return most recent conversation for this image
                        conversation_id = conversation_ids[-1]
                        conversation = self._conversations[conversation_id]
                        logger.debug(
                            f"Retrieved existing conversation {conversation_id} "
                            f"for image_id={image_id}"
                        )
                        return conversation

                # No existing conversation - create new one
                conversation_id = f"conv-{uuid.uuid4()}"
                conversation = Conversation(
                    conversation_id=conversation_id,
                    session_id=session_id,
                    image_id=image_id,
                )

                # Store in primary dict
                self._conversations[conversation_id] = conversation
                self._messages[conversation_id] = []

                # Update indexes
                if image_id:
                    self._conversations_by_image[image_id].append(conversation_id)
                self._conversations_by_session[session_id].append(conversation_id)

                logger.info(
                    f"Created new conversation {conversation_id} "
                    f"(image_id={image_id}, session_id={session_id})"
                )
                return conversation
        except Exception as e:
            logger.error(
                f"Failed to get or create conversation (image_id={image_id}, session_id={session_id}): {e}",
                exc_info=True,
            )
            # Fallback: create minimal conversation object
            conversation_id = f"conv-{uuid.uuid4()}"
            return Conversation(
                conversation_id=conversation_id,
                session_id=session_id,
                image_id=image_id,
            )

    def add_message(
        self, conversation_id: str, role: str, content: str
    ) -> Optional[Message]:
        """Add a message to conversation history.

        Implements graceful degradation (FR-012) - errors are logged but not
        raised, so history storage failures don't block chat requests.

        Args:
            conversation_id: Target conversation ID
            role: "user" or "assistant"
            content: Message text (max 50,000 characters)

        Returns:
            Created Message object, or None if operation failed
        """
        try:
            with self._lock:
                # Verify conversation exists
                if conversation_id not in self._conversations:
                    logger.error(
                        f"Cannot add message: conversation {conversation_id} not found"
                    )
                    return None

                # Create message
                message_id = f"msg-{uuid.uuid4()}"
                message = Message(
                    message_id=message_id,
                    conversation_id=conversation_id,
                    role=role,
                    content=content,
                )

                # Store message
                self._messages[conversation_id].append(message)

                # Update conversation last_activity
                conversation = self._conversations[conversation_id]
                conversation.touch()

                logger.info(
                    f"✓ Added {role} message {message_id} to conversation {conversation_id} "
                    f"({len(content)} chars, ~{message.token_count} tokens)"
                )
                return message

        except ValueError as e:
            # Message validation failed (invalid role or content too long)
            logger.error(
                f"Message validation failed for conversation {conversation_id}: {e}",
                exc_info=True,
            )
            return None
        except Exception as e:
            # Unexpected error - log but don't raise (graceful degradation)
            logger.error(
                f"Failed to add message to conversation {conversation_id}: {e}",
                exc_info=True,
            )
            return None

    def get_messages(self, conversation_id: str) -> List[Message]:
        """Get all messages for a conversation in chronological order.

        Args:
            conversation_id: Conversation ID to retrieve messages for

        Returns:
            List of Message objects (may be empty if conversation not found)
        """
        try:
            with self._lock:
                if conversation_id not in self._messages:
                    logger.warning(
                        f"No messages found for conversation {conversation_id}"
                    )
                    return []

                messages = self._messages[conversation_id]
                logger.debug(
                    f"Retrieved {len(messages)} messages for conversation {conversation_id}"
                )
                return list(messages)  # Return copy to avoid external mutation
        except Exception as e:
            logger.error(
                f"Failed to retrieve messages for conversation {conversation_id}: {e}",
                exc_info=True,
            )
            return []  # Return empty list on error

    def get_context_for_ai(
        self, conversation_id: str, max_messages: int = 50, max_tokens: int = 10_000
    ) -> List[Dict[str, str]]:
        """Get conversation history formatted for AI context injection.

        Implements context truncation (FR-015): Returns last N messages or
        up to M tokens, whichever limit is reached first. This prevents
        exceeding AI model context windows.

        Format matches OpenAI API messages array (Decision 6 in research.md):
        [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]

        Args:
            conversation_id: Conversation to retrieve context from
            max_messages: Maximum number of messages to include (default: 50)
            max_tokens: Maximum tokens to include (default: 10,000)

        Returns:
            List of message dicts in OpenAI format, ordered chronologically
        """
        try:
            with self._lock:
                messages = self._messages.get(conversation_id, [])

                if not messages:
                    return []

                # Truncation algorithm: Start from most recent, work backwards
                context: List[Dict[str, str]] = []
                total_tokens = 0

                for msg in reversed(messages):
                    # Check both limits
                    if len(context) >= max_messages or total_tokens >= max_tokens:
                        break

                    # Add message to context (will be reversed later)
                    context.insert(
                        0,  # Insert at beginning to maintain chronological order
                        {"role": msg.role, "content": msg.content},
                    )
                    total_tokens += msg.token_count

                logger.debug(
                    f"Retrieved context for conversation {conversation_id}: "
                    f"{len(context)} messages, ~{total_tokens} tokens"
                )
                return context
        except Exception as e:
            logger.error(
                f"Failed to retrieve context for conversation {conversation_id}: {e}",
                exc_info=True,
            )
            return []  # Return empty context on error

    def get_conversations_by_image(self, image_id: str) -> List[Conversation]:
        """Get all conversations associated with an image.

        Args:
            image_id: Image ID to look up

        Returns:
            List of Conversation objects (may be empty)
        """
        try:
            with self._lock:
                conversation_ids = self._conversations_by_image.get(image_id, [])
                conversations = [
                    self._conversations[cid]
                    for cid in conversation_ids
                    if cid in self._conversations
                ]
                logger.debug(
                    f"Found {len(conversations)} conversations for image {image_id}"
                )
                return conversations
        except Exception as e:
            logger.error(
                f"Failed to retrieve conversations for image {image_id}: {e}",
                exc_info=True,
            )
            return []  # Return empty list on error

    def get_conversations_by_session(self, session_id: str) -> List[Conversation]:
        """Get all conversations in a session.

        Args:
            session_id: Session ID to look up

        Returns:
            List of Conversation objects (may be empty)
        """
        try:
            with self._lock:
                conversation_ids = self._conversations_by_session.get(session_id, [])
                conversations = [
                    self._conversations[cid]
                    for cid in conversation_ids
                    if cid in self._conversations
                ]
                logger.debug(
                    f"Found {len(conversations)} conversations for session {session_id}"
                )
                return conversations
        except Exception as e:
            logger.error(
                f"Failed to retrieve conversations for session {session_id}: {e}",
                exc_info=True,
            )
            return []  # Return empty list on error

    def cleanup_old_conversations(
        self, retention_days: int, grace_period_days: int
    ) -> int:
        """Remove conversations older than retention period.

        Only deletes conversations where last_activity is older than
        (retention_days + grace_period_days). This prevents deleting
        active conversations that users are still engaged with.

        Args:
            retention_days: Base retention period (e.g., 30 days)
            grace_period_days: Additional grace period for active conversations (e.g., 7 days)

        Returns:
            Number of conversations deleted
        """
        try:
            with self._lock:
                cutoff_time = datetime.utcnow().timestamp() - (
                    (retention_days + grace_period_days) * 86400
                )
                deleted_count = 0
                to_delete = []

                # Find conversations to delete
                for conversation_id, conversation in self._conversations.items():
                    if conversation.last_activity.timestamp() < cutoff_time:
                        to_delete.append(conversation_id)

                # Delete conversations and update indexes
                for conversation_id in to_delete:
                    conversation = self._conversations[conversation_id]

                    # Remove from primary storage
                    del self._conversations[conversation_id]
                    del self._messages[conversation_id]

                    # Remove from indexes
                    if conversation.image_id:
                        if conversation.image_id in self._conversations_by_image:
                            self._conversations_by_image[conversation.image_id].remove(
                                conversation_id
                            )
                            # Clean up empty index entries
                            if not self._conversations_by_image[conversation.image_id]:
                                del self._conversations_by_image[conversation.image_id]

                    if conversation.session_id in self._conversations_by_session:
                        self._conversations_by_session[conversation.session_id].remove(
                            conversation_id
                        )
                        # Clean up empty index entries
                        if not self._conversations_by_session[conversation.session_id]:
                            del self._conversations_by_session[conversation.session_id]

                    deleted_count += 1

                if deleted_count > 0:
                    logger.info(
                        f"Cleaned up {deleted_count} conversations older than "
                        f"{retention_days + grace_period_days} days"
                    )
                else:
                    logger.debug("No conversations eligible for cleanup")

                return deleted_count
        except Exception as e:
            logger.error(
                f"Failed to cleanup old conversations: {e}",
                exc_info=True,
            )
            return 0  # Return 0 deleted on error


def start_cleanup_thread(
    conversation_service: ConversationService,
    cleanup_interval_seconds: int,
    retention_days: int,
    grace_period_days: int,
) -> threading.Thread:
    """Start background thread for periodic conversation cleanup.

    Creates a daemon thread that runs cleanup every N seconds. The thread
    runs asynchronously and doesn't block user requests (FR-017).

    Args:
        conversation_service: Service instance to clean up
        cleanup_interval_seconds: Seconds between cleanup runs (e.g., 3600 for hourly)
        retention_days: Base retention period
        grace_period_days: Grace period for active conversations

    Returns:
        Thread object (already started)
    """

    def cleanup_loop():
        """Cleanup loop that runs in background thread."""
        logger.info(
            f"Cleanup thread started: running every {cleanup_interval_seconds}s, "
            f"retention {retention_days}d + grace {grace_period_days}d"
        )

        while True:
            try:
                # Sleep first to avoid immediate cleanup on startup
                threading.Event().wait(cleanup_interval_seconds)

                # Run cleanup
                conversation_service.cleanup_old_conversations(
                    retention_days=retention_days, grace_period_days=grace_period_days
                )

            except Exception as e:
                # Log errors but don't crash the cleanup thread
                logger.error(f"Error in cleanup thread: {e}", exc_info=True)

    # Create and start daemon thread
    thread = threading.Thread(target=cleanup_loop, daemon=True, name="history-cleanup")
    thread.start()

    logger.info("Conversation history cleanup thread started")
    return thread
