"""Image validation and processing service."""

import base64
import io
import os
import threading
import uuid
from datetime import datetime
from typing import Dict, Optional, Tuple

from PIL import Image as PILImage
from werkzeug.datastructures import FileStorage

from src.models.image import Image
from src.utils.security import secure_filename


class ImageService:
    """Thread-safe service for image validation and storage."""

    # Magic number signatures for supported formats
    MAGIC_NUMBERS = {
        b"\xff\xd8\xff": "jpeg",
        b"\x89PNG\r\n\x1a\n": "png",
        b"GIF87a": "gif",
        b"GIF89a": "gif",
        b"RIFF": "webp",  # WebP files start with RIFF
    }

    def __init__(self, upload_folder: str, max_size_bytes: int, max_width: int, max_height: int):
        """Initialize image service.

        Args:
            upload_folder: Directory to store uploaded images
            max_size_bytes: Maximum file size in bytes
            max_width: Maximum image width in pixels
            max_height: Maximum image height in pixels
        """
        self.upload_folder = upload_folder
        self.max_size_bytes = max_size_bytes
        self.max_width = max_width
        self.max_height = max_height

        self._images: Dict[str, Image] = {}
        self._lock = threading.RLock()

        # Ensure upload folder exists
        os.makedirs(upload_folder, exist_ok=True)

    def validate_file_type(self, file_storage: FileStorage) -> Tuple[bool, Optional[str]]:
        """Validate file type using magic number verification.

        Args:
            file_storage: Uploaded file

        Returns:
            Tuple of (is_valid, detected_format or error_message)
        """
        # Read first bytes for magic number check
        file_storage.seek(0)
        header = file_storage.read(12)
        file_storage.seek(0)

        # Check magic numbers
        for magic, format_name in self.MAGIC_NUMBERS.items():
            if header.startswith(magic):
                return True, format_name

        return False, "Unsupported file type. Accepted: JPEG, PNG, GIF, WebP"

    def validate_file_size(self, file_storage: FileStorage) -> Tuple[bool, Optional[str]]:
        """Validate file size.

        Args:
            file_storage: Uploaded file

        Returns:
            Tuple of (is_valid, error_message if invalid)
        """
        file_storage.seek(0, os.SEEK_END)
        size = file_storage.tell()
        file_storage.seek(0)

        if size > self.max_size_bytes:
            max_mb = self.max_size_bytes / (1024 * 1024)
            return False, f"Image file exceeds maximum size of {max_mb:.0f}MB"

        return True, None

    def validate_and_extract_metadata(
        self, file_storage: FileStorage
    ) -> Tuple[bool, Optional[dict], Optional[str]]:
        """Validate image content and extract metadata using Pillow.

        Args:
            file_storage: Uploaded file

        Returns:
            Tuple of (is_valid, metadata_dict, error_or_corruption_message)
        """
        file_storage.seek(0)

        try:
            # Open image with Pillow
            img = PILImage.open(file_storage)

            # Verify image integrity
            try:
                img.verify()
            except Exception as e:
                # Image is corrupted
                return False, None, f"Image appears corrupted: {str(e)}"

            # Re-open after verify (verify closes the file)
            file_storage.seek(0)
            img = PILImage.open(file_storage)

            # Extract metadata
            width, height = img.size
            format_name = img.format
            mode = img.mode

            # Validate dimensions
            if width > self.max_width or height > self.max_height:
                return (
                    False,
                    None,
                    f"Image dimensions ({width}x{height}) exceed maximum ({self.max_width}x{self.max_height})",
                )

            metadata = {
                "width": width,
                "height": height,
                "format": format_name,
                "mode": mode,
            }

            return True, metadata, None

        except PILImage.DecompressionBombError:
            return False, None, "Image file is too large when decompressed"
        except (IOError, SyntaxError) as e:
            return False, None, f"Unable to process image: {str(e)}"
        except Exception as e:
            return False, None, f"Metadata extraction failed: {str(e)}"

    def generate_preview(self, file_storage: FileStorage, thumbnail_size: int = 200) -> Optional[str]:
        """Generate base64-encoded preview thumbnail for corrupted images.

        Args:
            file_storage: Uploaded file
            thumbnail_size: Thumbnail size in pixels

        Returns:
            Base64-encoded PNG thumbnail or None if generation fails
        """
        try:
            file_storage.seek(0)
            img = PILImage.open(file_storage)

            # Create thumbnail
            img.thumbnail((thumbnail_size, thumbnail_size))

            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            preview_base64 = base64.b64encode(buffer.read()).decode("utf-8")

            return preview_base64

        except Exception:
            return None

    def save_image_file(self, file_storage: FileStorage, original_filename: str) -> Tuple[str, str]:
        """Save image file to disk with UUID filename.

        Args:
            file_storage: Uploaded file
            original_filename: Original filename from upload

        Returns:
            Tuple of (image_id, file_path)
        """
        # Generate unique ID and secure filename
        image_id = str(uuid.uuid4())
        secured_name = secure_filename(original_filename)
        extension = secured_name.rsplit(".", 1)[1] if "." in secured_name else "bin"
        filename = f"{image_id}.{extension}"
        file_path = os.path.join(self.upload_folder, filename)

        # Save file
        file_storage.seek(0)
        file_storage.save(file_path)

        return image_id, file_path

    def add_image(self, image: Image) -> None:
        """Add image to store (thread-safe).

        Args:
            image: Image model instance
        """
        with self._lock:
            self._images[image.id] = image

    def get_image(self, image_id: str) -> Optional[Image]:
        """Retrieve image from store (thread-safe).

        Args:
            image_id: Image ID

        Returns:
            Image instance or None if not found
        """
        with self._lock:
            return self._images.get(image_id)

    def process_upload(
        self, file_storage: FileStorage, original_filename: str
    ) -> Tuple[Optional[Image], Optional[dict]]:
        """Process complete upload workflow with validation.

        Args:
            file_storage: Uploaded file
            original_filename: Original filename

        Returns:
            Tuple of (Image instance or None, error_dict if failed)
        """
        # Step 1: Validate file type
        is_valid, result = self.validate_file_type(file_storage)
        if not is_valid:
            return None, {"error": result, "code": "unsupported_format"}

        # Step 2: Validate file size
        is_valid, error = self.validate_file_size(file_storage)
        if not is_valid:
            return None, {"error": error, "code": "image_too_large"}

        # Step 3: Validate content and extract metadata
        is_valid, metadata, error_msg = self.validate_and_extract_metadata(file_storage)

        if not is_valid and "corrupted" in error_msg.lower():
            # Image is corrupted - generate preview
            preview_data = self.generate_preview(file_storage)

            # Create Image with suspected corruption status
            image_id = str(uuid.uuid4())
            corrupted_image = Image(
                id=image_id,
                filename=secure_filename(original_filename),
                size_bytes=0,  # Unknown due to corruption
                width=0,
                height=0,
                format="unknown",
                mode="unknown",
                file_path="",  # Not saved yet
                uploaded_at=datetime.utcnow(),
                corruption_status="suspected",
                preview_data=preview_data,
            )

            return None, {
                "error": "Image appears corrupted",
                "code": "corruption_suspected",
                "image_id": image_id,
                "preview_base64": preview_data,
                "corrupted_image": corrupted_image,
            }

        if not is_valid:
            return None, {"error": error_msg, "code": "validation_failed"}

        # Step 4: Save image file
        image_id, file_path = self.save_image_file(file_storage, original_filename)

        # Step 5: Create Image model
        image = Image(
            id=image_id,
            filename=secure_filename(original_filename),
            size_bytes=metadata.get("size_bytes", 0),
            width=metadata["width"],
            height=metadata["height"],
            format=metadata["format"],
            mode=metadata["mode"],
            file_path=file_path,
            uploaded_at=datetime.utcnow(),
            corruption_status="valid",
        )

        # Step 6: Add to store
        self.add_image(image)

        return image, None
