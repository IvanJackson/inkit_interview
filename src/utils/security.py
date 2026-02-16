"""Input validation and security utilities."""

import re
from typing import Optional
from werkzeug.utils import secure_filename as werkzeug_secure_filename


# Patterns for injection detection
SQL_INJECTION_PATTERN = re.compile(
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION)\b)",
    re.IGNORECASE,
)

XSS_PATTERN = re.compile(
    r"(<script|javascript:|onerror=|onload=|<iframe|<object|<embed)",
    re.IGNORECASE,
)

PATH_TRAVERSAL_PATTERN = re.compile(r"\.\./|\.\.\\")


def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """Sanitize user text input.

    Args:
        text: User-provided text
        max_length: Maximum allowed length (optional)

    Returns:
        Sanitized text

    Raises:
        ValueError: If text contains injection attempts or exceeds max_length
    """
    if not isinstance(text, str):
        raise ValueError("Text must be a string")

    # Check length
    if max_length and len(text) > max_length:
        raise ValueError(f"Text exceeds maximum length of {max_length} characters")

    # Detect SQL injection attempts
    if SQL_INJECTION_PATTERN.search(text):
        raise ValueError("Text contains potentially malicious SQL patterns")

    # Detect XSS attempts
    if XSS_PATTERN.search(text):
        raise ValueError("Text contains potentially malicious script patterns")

    # Basic sanitization - strip leading/trailing whitespace
    sanitized = text.strip()

    return sanitized


def validate_prompt(prompt: str, max_length: int = 10_000) -> str:
    """Validate and sanitize a chat prompt.

    Args:
        prompt: User's chat prompt
        max_length: Maximum allowed length (default: 10,000)

    Returns:
        Sanitized prompt

    Raises:
        ValueError: If prompt is invalid or contains malicious content
    """
    if not prompt:
        raise ValueError("Prompt cannot be empty")

    return sanitize_text(prompt, max_length=max_length)


def secure_filename(filename: str) -> str:
    """Secure a filename for safe storage.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for filesystem storage

    Raises:
        ValueError: If filename contains path traversal attempts
    """
    # Check for path traversal
    if PATH_TRAVERSAL_PATTERN.search(filename):
        raise ValueError("Filename contains path traversal patterns")

    # Use Werkzeug's secure_filename
    secured = werkzeug_secure_filename(filename)

    if not secured:
        raise ValueError("Filename resulted in empty string after sanitization")

    return secured


def validate_unicode_text(text: str) -> bool:
    """Validate that text is valid Unicode without control characters.

    Args:
        text: Text to validate

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(text, str):
        return False

    # Check for control characters (except newline, tab, carriage return)
    for char in text:
        code = ord(char)
        # Allow: tab (9), newline (10), carriage return (13), printable ASCII (32-126)
        # and Unicode characters (>= 128)
        if code < 32 and code not in (9, 10, 13):
            return False

    return True


def detect_injection_attempt(text: str) -> bool:
    """Detect potential injection attempts in text.

    Args:
        text: Text to check

    Returns:
        True if potential injection detected, False otherwise
    """
    return bool(
        SQL_INJECTION_PATTERN.search(text)
        or XSS_PATTERN.search(text)
        or PATH_TRAVERSAL_PATTERN.search(text)
    )
