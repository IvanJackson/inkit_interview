"""Flask middleware for session management, error handling, and rate limiting."""

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


# Global limiter instance (initialized by init_middleware)
limiter = None


def init_middleware(app: Flask) -> None:
    """Initialize middleware for the Flask application.

    Args:
        app: Flask application instance
    """
    global limiter

    # Initialize Flask-Limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[app.config["GLOBAL_RATE_LIMIT"]],
        storage_uri=app.config["RATELIMIT_STORAGE_URI"],
        strategy=app.config["RATELIMIT_STRATEGY"],
        headers_enabled=True,  # Include rate limit headers in responses
    )


def get_session_id():
    """Extract session ID from request for rate limiting.

    Returns:
        Session ID from cookie or remote address as fallback
    """
    from flask import request

    # Try to get session from cookie
    session_cookie = request.cookies.get("va_session_id")
    if session_cookie:
        return session_cookie

    # Fallback to IP address
    return get_remote_address()
