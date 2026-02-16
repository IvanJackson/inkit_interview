"""Unit tests for input validation and security utilities."""

import pytest
from src.utils.security import (
    sanitize_text,
    validate_prompt,
    secure_filename,
    validate_unicode_text,
    detect_injection_attempt,
)


class TestTextSanitization:
    """Test text sanitization and validation."""

    def test_sanitize_text_basic(self):
        """Verify basic text sanitization strips whitespace."""
        assert sanitize_text("  hello world  ") == "hello world"
        assert sanitize_text("test") == "test"

    def test_sanitize_text_max_length(self):
        """Verify max_length enforcement."""
        with pytest.raises(ValueError, match="exceeds maximum length"):
            sanitize_text("a" * 101, max_length=100)

        # Should pass
        assert sanitize_text("a" * 100, max_length=100) == "a" * 100

    def test_sanitize_text_detects_sql_injection(self):
        """Verify SQL injection detection (FR-027, SC-018)."""
        malicious_inputs = [
            "SELECT * FROM users",
            "'; DROP TABLE users; --",
            "UNION SELECT password FROM accounts",
            "INSERT INTO admin VALUES",
        ]

        for malicious in malicious_inputs:
            with pytest.raises(ValueError, match="malicious SQL patterns"):
                sanitize_text(malicious)

    def test_sanitize_text_detects_xss(self):
        """Verify XSS detection (FR-027, SC-018)."""
        malicious_inputs = [
            "<script>alert('XSS')</script>",
            "javascript:void(0)",
            "<img onerror='alert(1)'>",
            "<iframe src='evil.com'>",
            "<object data='malware.swf'>",
        ]

        for malicious in malicious_inputs:
            with pytest.raises(ValueError, match="malicious script patterns"):
                sanitize_text(malicious)

    def test_sanitize_text_allows_safe_input(self):
        """Verify safe input passes validation (FR-026)."""
        safe_inputs = [
            "What do you see in this image?",
            "Tell me about the colors and composition.",
            "Is this a cat or a dog?",
            "Describe the scene in detail.",
        ]

        for safe in safe_inputs:
            assert sanitize_text(safe) == safe.strip()

    def test_sanitize_text_non_string(self):
        """Verify non-string input raises error."""
        with pytest.raises(ValueError, match="must be a string"):
            sanitize_text(123)


class TestPromptValidation:
    """Test chat prompt validation."""

    def test_validate_prompt_basic(self):
        """Verify basic prompt validation."""
        prompt = "What's in this image?"
        assert validate_prompt(prompt) == prompt

    def test_validate_prompt_empty(self):
        """Verify empty prompt rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_prompt("")

    def test_validate_prompt_max_length(self):
        """Verify prompt length limit (FR-026)."""
        # Default max: 10,000 chars
        long_prompt = "a" * 10_001
        with pytest.raises(ValueError, match="exceeds maximum length"):
            validate_prompt(long_prompt)

        # Should pass
        ok_prompt = "a" * 10_000
        assert validate_prompt(ok_prompt) == ok_prompt

    def test_validate_prompt_injection(self):
        """Verify prompt injection detection."""
        with pytest.raises(ValueError, match="malicious"):
            validate_prompt("<script>alert('test')</script>")


class TestFilenameSecuring:
    """Test filename sanitization."""

    def test_secure_filename_basic(self):
        """Verify basic filename securing."""
        assert secure_filename("test.jpg") == "test.jpg"
        assert secure_filename("my photo.png") == "my_photo.png"

    def test_secure_filename_path_traversal(self):
        """Verify path traversal detection."""
        with pytest.raises(ValueError, match="path traversal"):
            secure_filename("../etc/passwd")

        with pytest.raises(ValueError, match="path traversal"):
            secure_filename("..\\windows\\system32")

    def test_secure_filename_special_chars(self):
        """Verify special character handling."""
        # Should be sanitized by werkzeug
        result = secure_filename("test@#$%.jpg")
        assert ".." not in result
        assert "/" not in result

    def test_secure_filename_empty_result(self):
        """Verify error on empty result."""
        with pytest.raises(ValueError, match="empty string"):
            secure_filename("@#$%^&")


class TestUnicodeValidation:
    """Test Unicode text validation (FR-026)."""

    def test_validate_unicode_text_basic(self):
        """Verify basic Unicode support."""
        assert validate_unicode_text("Hello world")
        assert validate_unicode_text("Héllo wörld")  # Accented chars
        assert validate_unicode_text("你好世界")  # Chinese
        assert validate_unicode_text("مرحبا")  # Arabic
        assert validate_unicode_text("Привет")  # Cyrillic

    def test_validate_unicode_text_allows_safe_whitespace(self):
        """Verify allowed whitespace characters."""
        assert validate_unicode_text("Line 1\nLine 2")  # Newline
        assert validate_unicode_text("Tab\there")  # Tab
        assert validate_unicode_text("Return\rhere")  # Carriage return

    def test_validate_unicode_text_rejects_control_chars(self):
        """Verify control characters rejected."""
        # Control character \x00 (null byte)
        assert not validate_unicode_text("test\x00bad")
        # Control character \x01 (start of heading)
        assert not validate_unicode_text("test\x01bad")

    def test_validate_unicode_text_non_string(self):
        """Verify non-string rejected."""
        assert not validate_unicode_text(123)
        assert not validate_unicode_text(None)


class TestInjectionDetection:
    """Test injection attempt detection (SC-018)."""

    def test_detect_sql_injection(self):
        """Verify SQL injection detection."""
        assert detect_injection_attempt("SELECT * FROM users")
        assert detect_injection_attempt("'; DROP TABLE users; --")
        assert not detect_injection_attempt("What do you see?")

    def test_detect_xss(self):
        """Verify XSS detection."""
        assert detect_injection_attempt("<script>alert(1)</script>")
        assert detect_injection_attempt("javascript:void(0)")
        assert not detect_injection_attempt("Tell me about this image")

    def test_detect_path_traversal(self):
        """Verify path traversal detection."""
        assert detect_injection_attempt("../etc/passwd")
        assert detect_injection_attempt("..\\windows\\system32")
        assert not detect_injection_attempt("image.jpg")

    def test_detect_injection_clean_input(self):
        """Verify clean input passes (100% attack prevention - SC-018)."""
        clean_inputs = [
            "What colors do you see?",
            "Describe the scene",
            "Is this a landscape or portrait?",
            "Tell me about the composition",
        ]

        for clean in clean_inputs:
            assert not detect_injection_attempt(clean)
