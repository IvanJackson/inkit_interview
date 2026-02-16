"""Image model for uploaded images."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Image:
    """Represents an uploaded image file with validation state and metadata."""

    id: str  # UUID
    filename: str  # Original filename (sanitized)
    size_bytes: int  # File size in bytes
    width: int  # Image width in pixels
    height: int  # Image height in pixels
    format: str  # Image format (JPEG, PNG, GIF, WebP)
    mode: str  # Color mode (RGB, RGBA, etc.)
    file_path: str  # Storage path on filesystem
    uploaded_at: datetime  # Upload timestamp (UTC)
    corruption_status: str  # "valid", "suspected", "confirmed"
    preview_data: Optional[str] = None  # Base64-encoded preview for corrupted images
    vision_analysis: Optional[str] = None  # Initial AI vision analysis result

    def __post_init__(self):
        """Validate corruption status enum."""
        valid_statuses = {"valid", "suspected", "confirmed"}
        if self.corruption_status not in valid_statuses:
            raise ValueError(
                f"Invalid corruption_status: {self.corruption_status}. "
                f"Must be one of {valid_statuses}"
            )

    def is_valid(self) -> bool:
        """Check if image is valid (not corrupted)."""
        return self.corruption_status == "valid"

    def is_corrupted(self) -> bool:
        """Check if image is confirmed corrupted."""
        return self.corruption_status == "confirmed"

    def requires_confirmation(self) -> bool:
        """Check if image requires user confirmation."""
        return self.corruption_status == "suspected"
