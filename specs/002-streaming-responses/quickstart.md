# Quickstart: Streaming Chat Responses

**Feature**: 002-streaming-responses

## Quick Test

### 1. Start the server

```bash
python3 app.py
```

### 2. Test streaming via curl

```bash
curl -N -X POST http://127.0.0.1:5001/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "hello"}'
```

You should see SSE events arriving one at a time:
```
data: {"id":"chatcmpl-...","object":"chat.completion.chunk",...,"choices":[{"delta":{"role":"assistant","content":""},...}]}

data: {"id":"chatcmpl-...","object":"chat.completion.chunk",...,"choices":[{"delta":{"content":"Hello!"},...}]}

...

data: [DONE]
```

The `-N` flag disables curl's output buffering so you see chunks in real time.

### 3. Test non-streaming (backward compatibility)

```bash
curl -X POST http://127.0.0.1:5001/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "hello"}'
```

Should return a complete JSON response (unchanged from Phase 1).

### 4. Test via browser

Open `http://127.0.0.1:5001` — type a message and watch it stream in word-by-word.

### 5. Test error cases

```bash
# Missing prompt
curl -X POST http://127.0.0.1:5001/chat/stream \
  -H "Content-Type: application/json" \
  -d '{}'

# Should return 400 JSON error
```

## Integration Scenarios

### Scenario A: Frontend streaming with fallback

The frontend sends text-only messages to `/chat/stream`. If the stream fails (network error, non-200 status, or non-event-stream content type), it automatically retries with `/chat` to get the full response.

### Scenario B: Concurrent streams

Multiple browser tabs can stream simultaneously. Each receives its own independent response. The server tracks active connections and rejects new ones with 503 when at capacity.

### Scenario C: Image + streaming

Upload an image via `/upload`, then stream follow-up questions via `/chat/stream` with the image_id. The streaming response discusses the uploaded image.
