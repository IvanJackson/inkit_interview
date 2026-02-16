"""Chat request models."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ChatRequest:
    """Represents a user's question about an image."""

    id: str  # UUID
    session_id: str  # Session making the request
    prompt: str  # User's text question/prompt (1-10,000 characters)
    image_id: Optional[str] = None  # Explicit image ID override (if None, use session.current_image_id)
    created_at: datetime = None  # Request timestamp (UTC)
    queue_status: str = "immediate"  # "immediate" or "queued"

    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()

        # Validate queue_status
        valid_statuses = {"immediate", "queued"}
        if self.queue_status not in valid_statuses:
            raise ValueError(
                f"Invalid queue_status: {self.queue_status}. "
                f"Must be one of {valid_statuses}"
            )


@dataclass
class QueuedRequest:
    """Represents a chat request queued during image upload."""

    id: str  # UUID (queue ID for polling)
    chat_request: ChatRequest  # The original chat request
    upload_image_id: str  # ID of image being uploaded
    queued_at: datetime  # Queueing timestamp (UTC)
    session_id: str  # Session that made request
    response: Optional[dict] = None  # Response once processed
    status: str = "pending"  # "pending" or "completed"

    def __post_init__(self):
        """Validate status."""
        valid_statuses = {"pending", "completed"}
        if self.status not in valid_statuses:
            raise ValueError(
                f"Invalid status: {self.status}. Must be one of {valid_statuses}"
            )

    def is_completed(self) -> bool:
        """Check if request has been processed."""
        return self.status == "completed"
