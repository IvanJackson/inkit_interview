"""Logging configuration for Visual Assistant API."""

import logging
import sys
from datetime import datetime


def setup_logger(name: str = "visual_assistant", level: str = "INFO") -> logging.Logger:
    """Configure and return application logger.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Set level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    logger.handlers = []

    # Console handler with formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Format: [2026-02-15 12:34:56] INFO [module.function] Message
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger


# Create default logger
logger = setup_logger()


def log_upload_attempt(filename: str, size_bytes: int, session_id: str):
    """Log image upload attempt."""
    logger.info(f"Upload attempt: {filename} ({size_bytes} bytes) | Session: {session_id[:8]}...")


def log_upload_success(image_id: str, filename: str):
    """Log successful upload."""
    logger.info(f"Upload success: {image_id[:8]}... | {filename}")


def log_upload_failure(filename: str, reason: str):
    """Log upload failure."""
    logger.warning(f"Upload failed: {filename} | Reason: {reason}")


def log_chat_request(session_id: str, prompt_length: int, image_id: str = None):
    """Log chat request."""
    img_ref = f"Image: {image_id[:8]}..." if image_id else "Session image"
    logger.info(f"Chat request: Session {session_id[:8]}... | Prompt length: {prompt_length} | {img_ref}")


def log_chat_queued(queue_id: str, session_id: str):
    """Log queued chat request."""
    logger.info(f"Chat queued: {queue_id[:8]}... | Session: {session_id[:8]}... | Upload in progress")


def log_session_created(session_id: str, device_id: str):
    """Log new session creation."""
    logger.info(f"Session created: {session_id[:8]}... | Device: {device_id[:16]}...")


def log_session_restored(session_id: str):
    """Log session restoration."""
    logger.info(f"Session restored: {session_id[:8]}...")


def log_rate_limit_hit(endpoint: str, session_id: str = None):
    """Log rate limit hit."""
    session_ref = f"Session: {session_id[:8]}..." if session_id else "Unknown session"
    logger.warning(f"Rate limit exceeded: {endpoint} | {session_ref}")


def log_security_warning(event_type: str, details: str):
    """Log security-related events."""
    logger.warning(f"SECURITY: {event_type} | {details}")


def log_validation_error(field: str, error: str):
    """Log validation errors."""
    logger.debug(f"Validation error: {field} | {error}")


def log_error(error: Exception, context: str = ""):
    """Log application errors."""
    logger.error(f"Error in {context}: {type(error).__name__}: {str(error)}")
