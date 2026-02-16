"""Session model for user interaction tracking."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SessionContext:
    """Represents a user's interaction session with persistence across disconnections."""

    session_id: str  # UUID
    current_image_id: Optional[str] = None  # ID of most recently uploaded image
    conversation_topic: Optional[str] = None  # Current conversation topic summary (max 500 chars)
    browser_device_id: str = ""  # Browser/device fingerprint for isolation
    created_at: datetime = None  # Session creation timestamp (UTC)
    last_activity: datetime = None  # Last request timestamp (UTC)
    authenticated: bool = False  # Authentication status
    expired: bool = False  # Whether session has expired

    def __post_init__(self):
        """Initialize timestamps if not provided."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.last_activity is None:
            self.last_activity = datetime.utcnow()

    def touch(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()

    def is_expired(self, timeout_hours: int = 24) -> bool:
        """Check if session has expired.

        Args:
            timeout_hours: Session timeout in hours

        Returns:
            True if session is expired
        """
        if self.expired:
            return True

        time_since_activity = datetime.utcnow() - self.last_activity
        hours_inactive = time_since_activity.total_seconds() / 3600

        return hours_inactive > timeout_hours

    def has_image(self) -> bool:
        """Check if session has an active image."""
        return self.current_image_id is not None
