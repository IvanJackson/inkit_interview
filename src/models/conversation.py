"""Conversation model for multi-turn dialogue history."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Conversation:
    """Represents a multi-turn conversation between user and assistant.

    Conversations are associated with an image (optional) and belong to a session.
    Tracks creation time and last activity for retention/cleanup purposes.
    """

    conversation_id: str  # UUID format
    session_id: str  # References SessionContext.session_id
    image_id: Optional[str] = None  # References uploaded image, or None for text-only
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)

    def touch(self) -> None:
        """Update last_activity to current UTC time.

        Called whenever a new message is added to the conversation.
        """
        self.last_activity = datetime.utcnow()
