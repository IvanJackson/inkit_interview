"""Application configuration for Visual Assistant API."""

import os


class Config:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = False
    TESTING = False

    # Upload limits
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    MAX_IMAGE_WIDTH = 4096
    MAX_IMAGE_HEIGHT = 4096
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
    ALLOWED_EXTENSIONS = {"jpeg", "jpg", "png", "gif", "webp"}

    # Rate limiting
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_STRATEGY = "fixed-window"
    UPLOAD_RATE_LIMIT = "20 per hour"
    CHAT_RATE_LIMIT = "100 per minute"
    GLOBAL_RATE_LIMIT = "1000 per hour"

    # Session
    SESSION_TIMEOUT_HOURS = 24
    SESSION_COOKIE_NAME = "va_session_id"

    # Chat
    MAX_PROMPT_LENGTH = 10_000

    # OpenAI mock
    MOCK_MODEL_NAME = "gpt-4-vision-preview"
    MOCK_VISION_DELAY = 0.1  # seconds
    MOCK_CHAT_DELAY = 0.2  # seconds

    # Streaming (Question 2)
    MAX_STREAMING_CONNECTIONS = 50  # Max concurrent SSE connections
    STREAM_TIMEOUT_SECONDS = 30  # Max duration of a single stream

    # Silly excuses for upload-in-progress
    SILLY_EXCUSES = [
        "I went to the bathroom, be right back!",
        "I'm fetching the dog, one moment!",
        "I'm making coffee, hold on!",
        "I stepped out for some fresh air!",
        "I'm watering the plants, just a sec!",
        "I'm chasing a butterfly, almost done!",
        "I'm searching for my glasses, hang tight!",
        "I'm untangling my headphones, give me a moment!",
    ]


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    UPLOAD_FOLDER = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "test_uploads"
    )
    MOCK_VISION_DELAY = 0  # No delays in tests
    MOCK_CHAT_DELAY = 0
    STREAM_TIMEOUT_SECONDS = 5  # Short timeout for tests


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": Config,
}
