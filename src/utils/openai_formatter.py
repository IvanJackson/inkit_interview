"""OpenAI-compatible response formatting utilities.

Two distinct formats are used to match the actual OpenAI API:
- Vision Analysis: OpenAI Responses API format (output array with message objects)
- Chat Completion: OpenAI Chat Completions API format (choices array with message objects)
"""

import time
import uuid
from typing import Optional


def format_chat_completion(
    content: str,
    model: str = "gpt-4-vision-preview",
    finish_reason: str = "stop",
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
) -> dict:
    """Format a chat completion response in OpenAI Chat Completions API format.

    Args:
        content: The assistant's response text
        model: Model name (default: gpt-4-vision-preview)
        finish_reason: Reason completion finished ("stop", "length", "content_filter")
        prompt_tokens: Mock token count for prompt
        completion_tokens: Mock token count for completion

    Returns:
        OpenAI Chat Completions API response dictionary
    """
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "logprobs": None,
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "service_tier": "default",

        "system_fingerprint": None,
    }


def format_vision_analysis(
    content: str,
    model: str = "gpt-4-vision-preview",
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
) -> dict:
    """Format a vision analysis response in OpenAI Responses API format.

    The Responses API uses a different structure from Chat Completions:
    - Top-level 'output' array containing message objects
    - Messages have 'content' arrays with typed content blocks
    - Content blocks use 'type: output_text' with 'text' and 'annotations'
    - Additional metadata fields like status, temperature, service_tier, etc.

    Args:
        content: The vision analysis text
        model: Model name (default: gpt-4-vision-preview)
        prompt_tokens: Mock token count for prompt
        completion_tokens: Mock token count for completion

    Returns:
        OpenAI Responses API format dictionary (matches actual API response)
    """
    msg_id = f"msg_{uuid.uuid4().hex[:32]}"
    resp_id = f"resp_{uuid.uuid4().hex[:32]}"
    timestamp = int(time.time())

    return {
        "id": resp_id,
        "object": "response",
        "created_at": float(timestamp),
        "completed_at": float(timestamp),
        "model": model,
        "status": "completed",
        "output": [
            {
                "id": msg_id,
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": content,
                        "annotations": [],
                        "logprobs": [],
                    }
                ],
                "status": "completed",
            }
        ],
        "usage": {
            "input_tokens": prompt_tokens,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens": completion_tokens,
            "output_tokens_details": {"reasoning_tokens": 0},
            "total_tokens": prompt_tokens + completion_tokens,
        },
        # Configuration fields
        "service_tier": "default",
        "temperature": 1.0,
        "top_p": 1.0,
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "tools": [],
        "top_logprobs": 0,
        "truncation": "disabled",
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        # Additional metadata fields from real API
        "error": None,
        "incomplete_details": None,
        "instructions": None,
        "metadata": {},
        "background": False,
        "conversation": None,
        "max_output_tokens": None,
        "max_tool_calls": None,
        "previous_response_id": None,
        "prompt": None,
        "prompt_cache_key": None,
        "prompt_cache_retention": None,
        "reasoning": {
            "effort": None,
            "generate_summary": None,
            "summary": None,
        },
        "safety_identifier": None,
        "text": {
            "format": {"type": "text"},
            "verbosity": "medium",
        },
        "user": None,
        "billing": {"payer": "developer"},
        "store": True,
    }


def format_error_response(
    message: str,
    error_type: str = "invalid_request_error",
    param: Optional[str] = None,
    code: Optional[str] = None,
) -> dict:
    """Format an error response in OpenAI format.

    Args:
        message: Clear, actionable error message
        error_type: Error type ("invalid_request_error", "rate_limit_exceeded", "api_error")
        param: Parameter that caused the error (optional)
        code: Error code (optional)

    Returns:
        OpenAI-compatible error response dictionary
    """
    error = {
        "message": message,
        "type": error_type,
    }

    if param:
        error["param"] = param

    if code:
        error["code"] = code

    return {"error": error}


def format_silly_excuse(excuse: str) -> dict:
    """Format a silly excuse as a chat completion response.

    Args:
        excuse: The silly excuse text

    Returns:
        OpenAI-compatible chat completion with the excuse
    """
    return format_chat_completion(
        content=excuse,
        prompt_tokens=10,
        completion_tokens=20,
    )


def format_photo_relevance_prompt(prompt: str) -> dict:
    """Format a photo relevance prompt as a chat completion response.

    Args:
        prompt: The relevance prompt text (e.g., "This looks like a different topic...")

    Returns:
        OpenAI-compatible chat completion with the relevance prompt
    """
    return format_chat_completion(
        content=prompt,
        prompt_tokens=50,
        completion_tokens=30,
    )
