"""Message model for individual conversation turns."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    """Represents a single message in a conversation.

    Can be from either the user or the assistant (role field).
    Includes token count estimation for context window management.
    """

    message_id: str  # UUID format
    conversation_id: str  # References Conversation.conversation_id
    role: str  # "user" or "assistant"
    content: str  # Message text, max 50,000 characters
    created_at: datetime = field(default_factory=datetime.utcnow)
    token_count: int = 0  # Estimated as word_count * 2

    def __post_init__(self) -> None:
        """Validate message and compute token count if not provided."""
        # Validate role
        valid_roles = {"user", "assistant"}
        if self.role not in valid_roles:
            raise ValueError(
                f"Invalid role: {self.role}. Must be one of {valid_roles}"
            )

        # Validate content length
        if len(self.content) > 50_000:
            raise ValueError(
                f"Content exceeds maximum length of 50,000 characters "
                f"(got {len(self.content)})"
            )

        # Compute token count if not explicitly provided
        if self.token_count == 0:
            # Rough estimation: word_count * 2
            # This matches the pattern in mock_openai_service.py
            self.token_count = len(self.content.split()) * 2
