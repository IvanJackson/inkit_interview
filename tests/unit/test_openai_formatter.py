"""Unit tests for OpenAI response formatter utilities."""

import pytest
from src.utils.openai_formatter import (
    format_chat_completion,
    format_vision_analysis,
    format_error_response,
    format_silly_excuse,
    format_photo_relevance_prompt,
)


class TestChatCompletionFormat:
    """Test chat completion response formatting (Chat Completions API)."""

    def test_format_chat_completion_has_required_fields(self):
        """Verify chat completion has all OpenAI-required fields."""
        response = format_chat_completion("Test response")

        # Check top-level fields
        assert "id" in response
        assert response["id"].startswith("chatcmpl-")
        assert response["object"] == "chat.completion"
        assert "created" in response
        assert isinstance(response["created"], int)
        assert response["model"] == "gpt-4-vision-preview"
        assert "choices" in response
        assert "usage" in response

    def test_format_chat_completion_has_optional_fields(self):
        """Verify chat completion includes optional fields per OpenAI spec."""
        response = format_chat_completion("Test response")

        assert "service_tier" in response
        assert response["service_tier"] == "default"
        assert "system_fingerprint" in response
        assert response["system_fingerprint"] is None

    def test_format_chat_completion_choices_structure(self):
        """Verify choices array structure matches OpenAI format."""
        response = format_chat_completion("Test response")
        choices = response["choices"]

        assert len(choices) == 1
        choice = choices[0]
        assert choice["index"] == 0
        assert "message" in choice
        assert choice["message"]["role"] == "assistant"
        assert choice["message"]["content"] == "Test response"
        assert "finish_reason" in choice
        assert choice["finish_reason"] == "stop"
        assert "logprobs" in choice
        assert choice["logprobs"] is None

    def test_format_chat_completion_usage_structure(self):
        """Verify usage statistics structure."""
        response = format_chat_completion(
            "Test", prompt_tokens=100, completion_tokens=50
        )
        usage = response["usage"]

        assert usage["prompt_tokens"] == 100
        assert usage["completion_tokens"] == 50
        assert usage["total_tokens"] == 150

    def test_format_chat_completion_finish_reasons(self):
        """Verify different finish_reason values are supported."""
        for reason in ["stop", "length", "content_filter"]:
            response = format_chat_completion("Test", finish_reason=reason)
            assert response["choices"][0]["finish_reason"] == reason


class TestVisionAnalysisFormat:
    """Test vision analysis response formatting (Responses API)."""

    def test_format_vision_analysis_uses_responses_api_format(self):
        """Verify vision analysis uses Responses API format, NOT Chat Completions."""
        response = format_vision_analysis("This image shows a cat")

        # Responses API uses different top-level structure
        assert response["id"].startswith("resp_")
        assert response["object"] == "response"
        assert "created_at" in response
        assert isinstance(response["created_at"], (int, float))
        assert "output" in response

        # Should NOT have Chat Completions fields
        assert "choices" not in response
        assert "created" not in response

    def test_format_vision_analysis_output_structure(self):
        """Verify output array matches Responses API message format."""
        response = format_vision_analysis("This image shows a cat")
        output = response["output"]

        assert isinstance(output, list)
        assert len(output) == 1

        message = output[0]
        assert message["id"].startswith("msg_")
        assert message["type"] == "message"
        assert message["role"] == "assistant"
        assert message["status"] == "completed"

    def test_format_vision_analysis_content_blocks(self):
        """Verify content blocks use output_text type with annotations."""
        response = format_vision_analysis("This image shows a cat")
        content = response["output"][0]["content"]

        assert isinstance(content, list)
        assert len(content) == 1

        block = content[0]
        assert block["type"] == "output_text"
        assert block["text"] == "This image shows a cat"
        assert block["annotations"] == []

    def test_format_vision_analysis_usage_structure(self):
        """Verify Responses API uses input_tokens/output_tokens naming."""
        response = format_vision_analysis(
            "Test", prompt_tokens=100, completion_tokens=50
        )
        usage = response["usage"]

        # Responses API uses input_tokens/output_tokens, NOT prompt_tokens/completion_tokens
        assert usage["input_tokens"] == 100
        assert usage["output_tokens"] == 50
        assert usage["total_tokens"] == 150

    def test_format_vision_analysis_extracts_text(self):
        """Verify the analysis text can be extracted from the Responses API format."""
        text = "A detailed description of the image"
        response = format_vision_analysis(text)

        # This is how consumers should extract text from Responses API
        extracted = response["output"][0]["content"][0]["text"]
        assert extracted == text


class TestErrorResponseFormat:
    """Test error response formatting."""

    def test_format_error_response_basic(self):
        """Verify basic error response structure."""
        response = format_error_response(
            message="Test error", error_type="invalid_request_error"
        )

        assert "error" in response
        error = response["error"]
        assert error["message"] == "Test error"
        assert error["type"] == "invalid_request_error"

    def test_format_error_response_with_param(self):
        """Verify error response with param field."""
        response = format_error_response(
            message="Invalid image",
            error_type="invalid_request_error",
            param="image",
        )

        assert response["error"]["param"] == "image"

    def test_format_error_response_with_code(self):
        """Verify error response with code field."""
        response = format_error_response(
            message="Too large",
            error_type="invalid_request_error",
            code="image_too_large",
        )

        assert response["error"]["code"] == "image_too_large"

    def test_format_error_response_all_fields(self):
        """Verify error response with all optional fields."""
        response = format_error_response(
            message="Complete error",
            error_type="invalid_request_error",
            param="image",
            code="validation_failed",
        )

        error = response["error"]
        assert error["message"] == "Complete error"
        assert error["type"] == "invalid_request_error"
        assert error["param"] == "image"
        assert error["code"] == "validation_failed"


class TestSpecialResponses:
    """Test special response types (silly excuses, photo relevance)."""

    def test_format_silly_excuse(self):
        """Verify silly excuse formatted as chat completion."""
        response = format_silly_excuse("I went to the bathroom!")

        assert response["id"].startswith("chatcmpl-")
        assert response["object"] == "chat.completion"
        assert response["choices"][0]["message"]["content"] == "I went to the bathroom!"

    def test_format_photo_relevance_prompt(self):
        """Verify photo relevance prompt formatted as chat completion."""
        prompt_text = "This looks like a different topic - would you like to start a new conversation?"
        response = format_photo_relevance_prompt(prompt_text)

        assert response["id"].startswith("chatcmpl-")
        assert response["object"] == "chat.completion"
        assert response["choices"][0]["message"]["content"] == prompt_text


class TestOpenAICompatibility:
    """Test responses are compatible with OpenAI client libraries."""

    def test_chat_completion_client_compatible(self):
        """Verify chat completion response can be consumed by OpenAI client libraries."""
        response = format_chat_completion("Test response")

        # Required fields for OpenAI Chat Completions client compatibility
        required_fields = ["id", "object", "created", "model", "choices", "usage"]
        for f in required_fields:
            assert f in response

        # Choices structure
        assert isinstance(response["choices"], list)
        assert len(response["choices"]) > 0
        choice = response["choices"][0]
        assert "index" in choice
        assert "message" in choice
        assert "finish_reason" in choice
        assert "logprobs" in choice

        # Message structure
        message = choice["message"]
        assert "role" in message
        assert "content" in message

        # Usage structure
        usage = response["usage"]
        assert "prompt_tokens" in usage
        assert "completion_tokens" in usage
        assert "total_tokens" in usage

    def test_vision_analysis_responses_api_compatible(self):
        """Verify vision analysis follows Responses API format."""
        response = format_vision_analysis("Test analysis")

        # Required Responses API fields
        assert response["id"].startswith("resp_")
        assert response["object"] == "response"
        assert "created_at" in response
        assert "output" in response
        assert "usage" in response

        # Output structure
        msg = response["output"][0]
        assert msg["id"].startswith("msg_")
        assert msg["type"] == "message"
        assert msg["role"] == "assistant"
        assert msg["content"][0]["type"] == "output_text"

    def test_formats_are_distinct(self):
        """Verify vision and chat use fundamentally different structures."""
        vision = format_vision_analysis("Vision test")
        chat = format_chat_completion("Chat test")

        # Vision uses Responses API
        assert "output" in vision
        assert "choices" not in vision
        assert vision["object"] == "response"

        # Chat uses Chat Completions API
        assert "choices" in chat
        assert "output" not in chat
        assert chat["object"] == "chat.completion"
