"""Response models for OpenAI-compatible API responses.

Two distinct formats:
- Chat Completions API: Traditional format with choices array (for chat)
- Responses API: Newer format with output array (for vision analysis)
"""

from dataclasses import dataclass, field
from typing import List, Optional


# ---- Chat Completions API Models ----


@dataclass
class Message:
    """OpenAI Chat Completions message format."""

    role: str  # "assistant", "user", "system"
    content: str


@dataclass
class Choice:
    """OpenAI Chat Completions choice format."""

    index: int
    message: Message
    finish_reason: str  # "stop", "length", "content_filter", or null
    logprobs: Optional[dict] = None


@dataclass
class CompletionUsage:
    """OpenAI Chat Completions token usage statistics."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class ChatCompletionResponse:
    """OpenAI Chat Completions API response format."""

    id: str  # Format: "chatcmpl-{unique_id}"
    object: str  # Always "chat.completion"
    created: int  # Unix timestamp
    model: str  # e.g., "gpt-4-vision-preview"
    choices: List[Choice]
    usage: CompletionUsage
    service_tier: Optional[str] = "default"
    system_fingerprint: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "object": self.object,
            "created": self.created,
            "model": self.model,
            "choices": [
                {
                    "index": choice.index,
                    "message": {
                        "role": choice.message.role,
                        "content": choice.message.content,
                    },
                    "logprobs": choice.logprobs,
                    "finish_reason": choice.finish_reason,
                }
                for choice in self.choices
            ],
            "usage": {
                "prompt_tokens": self.usage.prompt_tokens,
                "completion_tokens": self.usage.completion_tokens,
                "total_tokens": self.usage.total_tokens,
            },
            "service_tier": self.service_tier,
            "system_fingerprint": self.system_fingerprint,
        }


# ---- Responses API Models (Vision Analysis) ----


@dataclass
class OutputText:
    """OpenAI Responses API output_text content block."""

    type: str = "output_text"
    text: str = ""
    annotations: List[dict] = field(default_factory=list)


@dataclass
class OutputMessage:
    """OpenAI Responses API message in the output array."""

    id: str  # Format: "msg_{unique_id}"
    type: str = "message"
    role: str = "assistant"
    content: List[OutputText] = field(default_factory=list)
    status: str = "completed"


@dataclass
class ResponsesUsage:
    """OpenAI Responses API token usage statistics."""

    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass
class VisionAnalysisResponse:
    """OpenAI Responses API format for vision analysis."""

    id: str  # Format: "resp_{unique_id}"
    object: str = "response"
    created_at: int = 0  # Unix timestamp
    model: str = "gpt-4-vision-preview"
    output: List[OutputMessage] = field(default_factory=list)
    usage: Optional[ResponsesUsage] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "object": self.object,
            "created_at": self.created_at,
            "model": self.model,
            "output": [
                {
                    "id": msg.id,
                    "type": msg.type,
                    "role": msg.role,
                    "content": [
                        {
                            "type": block.type,
                            "text": block.text,
                            "annotations": block.annotations,
                        }
                        for block in msg.content
                    ],
                    "status": msg.status,
                }
                for msg in self.output
            ],
            "usage": {
                "input_tokens": self.usage.input_tokens,
                "output_tokens": self.usage.output_tokens,
                "total_tokens": self.usage.total_tokens,
            } if self.usage else None,
        }


# ---- Error Response (shared) ----


@dataclass
class ErrorResponse:
    """OpenAI error response format."""

    message: str
    type: str  # "invalid_request_error", "rate_limit_exceeded", "api_error"
    param: Optional[str] = None
    code: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        error = {
            "message": self.message,
            "type": self.type,
        }

        if self.param:
            error["param"] = self.param

        if self.code:
            error["code"] = self.code

        return {"error": error}
