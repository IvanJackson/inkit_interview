# API Contract: POST /chat/stream

**Feature**: 002-streaming-responses
**Implements**: FR-001 through FR-014, FR-018 through FR-020

## Endpoint

```
POST /chat/stream
Content-Type: application/json
```

## Request

Same format as `POST /chat`:

```json
{
  "prompt": "What do you see in this image?",
  "image_id": "uuid"  // Optional
}
```

## Response: Success (200)

Content-Type: `text/event-stream`

### Headers

```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

### SSE Event Sequence

**1. Role chunk** (first event):
```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1700000000,"model":"gpt-4-vision-preview","choices":[{"index":0,"delta":{"role":"assistant","content":""},"logprobs":null,"finish_reason":null}],"usage":null,"service_tier":"default","system_fingerprint":null}

```

**2. Content chunks** (one per token):
```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1700000000,"model":"gpt-4-vision-preview","choices":[{"index":0,"delta":{"content":"Hello"},"logprobs":null,"finish_reason":null}],"usage":null,"service_tier":"default","system_fingerprint":null}

```

**3. Stop chunk**:
```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1700000000,"model":"gpt-4-vision-preview","choices":[{"index":0,"delta":{},"logprobs":null,"finish_reason":"stop"}],"usage":null,"service_tier":"default","system_fingerprint":null}

```

**4. Usage chunk**:
```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1700000000,"model":"gpt-4-vision-preview","choices":[{"index":0,"delta":{},"logprobs":null,"finish_reason":null}],"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15},"service_tier":"default","system_fingerprint":null}

```

**5. Done sentinel**:
```
data: [DONE]

```

## Response: Error Cases

All error responses are JSON (not SSE), returned before the stream begins.

### 400 Bad Request — Missing prompt
```json
{
  "error": {
    "message": "Missing required field: prompt",
    "type": "invalid_request_error",
    "code": "missing_prompt"
  }
}
```

### 400 Bad Request — Invalid prompt
```json
{
  "error": {
    "message": "Input contains potentially malicious content",
    "type": "invalid_request_error",
    "param": "prompt",
    "code": "invalid_prompt"
  }
}
```

### 202 — Upload in progress
```json
{
  "error": {
    "message": "Image upload in progress. Please try again shortly.",
    "type": "invalid_request_error",
    "code": "upload_in_progress"
  }
}
```

### 429 Too Many Requests
```json
{
  "error": {
    "message": "Rate limit exceeded. Please try again later.",
    "type": "rate_limit_exceeded",
    "code": "rate_limit_exceeded"
  }
}
```

### 503 Service Unavailable — Connection limit reached
```json
{
  "error": {
    "message": "Too many active streaming connections. Please try again shortly.",
    "type": "api_error",
    "code": "streaming_capacity_exceeded"
  }
}
```

## Validation Rules

- `prompt` is required, non-empty, max 10,000 characters
- `prompt` is sanitized for XSS, SQL injection, path traversal
- `image_id` is optional — if omitted, uses session's current image or text-only mode
- Rate limited: same as `/chat` (100 requests/minute per session)

## Test Scenarios

| Scenario | Input | Expected Status | Expected Behavior |
|----------|-------|-----------------|-------------------|
| Valid prompt, text-only | `{"prompt": "hello"}` | 200 | SSE stream with greeting response |
| Valid prompt, with image | `{"prompt": "describe", "image_id": "uuid"}` | 200 | SSE stream with image response |
| Missing prompt | `{}` | 400 | JSON error |
| Empty prompt | `{"prompt": ""}` | 400 | JSON error |
| Malicious prompt | `{"prompt": "<script>alert(1)</script>"}` | 400 | JSON error |
| Rate limited | (exceed limit) | 429 | JSON error |
| At connection capacity | (50+ active streams) | 503 | JSON error |
| Upload in progress | (image uploading) | 202 | JSON error |
| Content reassembly | Any valid prompt | 200 | Assembled deltas = non-streaming response |
