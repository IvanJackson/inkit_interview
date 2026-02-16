# Quickstart: Foundational API - Image Upload and Basic Chat

**Feature**: 001-foundational-api
**Date**: 2026-02-14

## Prerequisites

- Python 3.13+
- pipenv or pip
- A test image file (JPEG, PNG, GIF, or WebP; ≤16MB; ≤4096x4096px)

## Setup

```bash
# Clone and checkout the feature branch
git checkout 001-foundational-api

# Install dependencies (with new packages)
pipenv install
# Or with pip:
pip install -r requirements.txt
```

### New Dependencies (Phase 1)

Add the following to your environment:
- **Pillow** - Image validation, metadata extraction, corruption detection
- **Flask-Limiter** - Industry-standard rate limiting

```bash
pipenv install Pillow flask-limiter
# Or:
pip install Pillow flask-limiter
```

## Running the Server

```bash
pipenv run python3 app.py
# Or:
python3 app.py
```

The API will be available at `http://127.0.0.1:5000`.

## API Usage Examples

### 1. Upload an Image

```bash
curl -X POST http://127.0.0.1:5000/upload \
  -F "image=@photo.jpg"
```

**Success Response** (200):
```json
{
  "image_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "filename": "photo.jpg",
  "size_bytes": 2048576,
  "width": 1920,
  "height": 1080,
  "format": "JPEG",
  "analysis": {
    "id": "chatcmpl-abc123",
    "object": "chat.completion",
    "created": 1708000000,
    "model": "gpt-4-vision-preview",
    "choices": [{
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "This image shows a scenic landscape with mountains and a lake..."
      },
      "finish_reason": "stop"
    }],
    "usage": {
      "prompt_tokens": 100,
      "completion_tokens": 45,
      "total_tokens": 145
    }
  }
}
```

### 2. Chat About the Image (No Image ID Needed)

```bash
curl -X POST http://127.0.0.1:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What colors do you see in this image?"}'
```

**Success Response** (200):
```json
{
  "id": "chatcmpl-def456",
  "object": "chat.completion",
  "created": 1708000100,
  "model": "gpt-4-vision-preview",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "I can see blues from the lake and sky, greens from the trees, and whites from the snow-capped mountains."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 56,
    "completion_tokens": 31,
    "total_tokens": 87
  }
}
```

### 3. Chat With Explicit Image ID

```bash
curl -X POST http://127.0.0.1:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Describe the lighting in this photo",
    "image_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }'
```

### 4. Chat During Upload (Silly Excuse + Queuing)

If you send a chat request while an image is still uploading:

**Response** (202 Accepted):
```json
{
  "queued": true,
  "queue_id": "q-789xyz",
  "excuse": "I'm fetching the dog, one moment please!",
  "chat_response": {
    "id": "chatcmpl-excuse123",
    "object": "chat.completion",
    "created": 1708000200,
    "model": "gpt-4-vision-preview",
    "choices": [{
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "I'm fetching the dog, one moment please! Your question has been noted and I'll get back to you shortly."
      },
      "finish_reason": "stop"
    }],
    "usage": {
      "prompt_tokens": 10,
      "completion_tokens": 20,
      "total_tokens": 30
    }
  }
}
```

The queued request is automatically processed once the upload completes.

### 5. Photo Relevance (New Topic Detection)

When uploading a new unrelated image during a conversation, the system responds with:

```json
{
  "id": "chatcmpl-relevance456",
  "object": "chat.completion",
  "created": 1708000300,
  "model": "gpt-4-vision-preview",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "This looks like a different topic - would you like to start a new conversation?"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 18,
    "total_tokens": 33
  }
}
```

Confirm the switch:
```bash
curl -X POST http://127.0.0.1:5000/chat/relevance \
  -H "Content-Type: application/json" \
  -d '{"action": "start_new", "new_image_id": "new-uuid-here"}'
```

## Error Examples

### Invalid File Type (415)
```bash
curl -X POST http://127.0.0.1:5000/upload -F "image=@document.pdf"
```
```json
{
  "error": {
    "message": "Unsupported image format. Allowed types: JPEG, PNG, GIF, WebP",
    "type": "invalid_request_error",
    "param": "image",
    "code": "unsupported_format"
  }
}
```

### File Too Large (413)
```json
{
  "error": {
    "message": "Image file exceeds maximum size of 16MB",
    "type": "invalid_request_error",
    "param": "image",
    "code": "image_too_large"
  }
}
```

### No Image in Session (400)
```bash
# Chat without uploading first
curl -X POST http://127.0.0.1:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What do you see?"}'
```
```json
{
  "error": {
    "message": "Please upload an image first before starting a chat",
    "type": "invalid_request_error",
    "param": "image_id",
    "code": "no_image_in_session"
  }
}
```

### Rate Limit Exceeded (429)
```json
{
  "error": {
    "message": "Chat rate limit exceeded. Maximum 100 requests per minute. Please try again later.",
    "type": "rate_limit_exceeded",
    "param": null,
    "code": "rate_limit_exceeded"
  }
}
```

## Rate Limits

| Endpoint | Limit | Per |
|----------|-------|-----|
| POST /upload | 20 requests | hour / session |
| POST /chat | 100 requests | minute / session |
| All endpoints | 1000 requests | hour / IP |

Rate-limited responses include a `Retry-After` header indicating when the limit resets.

## Running Tests

```bash
# All tests
pipenv run pytest

# By category
pipenv run pytest tests/unit/
pipenv run pytest tests/integration/
pipenv run pytest tests/concurrent/

# Specific test
pipenv run pytest tests/unit/test_image_service.py -v
```

## Key Architecture Notes

- **Session-based context**: No need to pass image IDs on every chat request
- **All responses**: Match OpenAI chat completion format exactly
- **In-memory storage**: Phase 1 uses dictionaries (migrates to DB in Question 4)
- **Thread-safe**: All shared state protected with RLock for concurrent access
- **Rate limiting**: Flask-Limiter with in-memory backend (migrates to Redis in Question 4)
