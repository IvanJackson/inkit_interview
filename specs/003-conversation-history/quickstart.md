# Quickstart: Conversation History

**Feature**: 003-conversation-history
**Date**: 2026-02-16

## Prerequisites

- Flask dev server running on `http://localhost:5001`
- At least one image uploaded (for image-related scenarios)

---

## Scenario 1: Multi-Turn Conversation

Upload an image and ask three follow-up questions. History is automatically recorded and injected as context for each subsequent turn.

```bash
# Step 1: Upload an image
curl -X POST http://localhost:5001/upload \
  -F "image=@photo.jpg" \
  -c cookies.txt

# Response includes image_id:
# {"image_id": "abc-123", "status": "completed", ...}

# Step 2: First question about the image
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What do you see in this image?", "image_id": "abc-123"}' \
  -b cookies.txt -c cookies.txt

# Response: OpenAI-compatible chat completion with image description
# History now contains: 1 user message + 1 assistant response

# Step 3: Follow-up question (history automatically injected)
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Tell me more about the colors", "image_id": "abc-123"}' \
  -b cookies.txt -c cookies.txt

# The assistant now has context from the first exchange.
# History: 2 user messages + 2 assistant responses

# Step 4: Third follow-up
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "How would you improve the composition?", "image_id": "abc-123"}' \
  -b cookies.txt -c cookies.txt

# Full conversation context (all 6 messages) is available to the model.
```

**What happens internally**:
1. Each `POST /chat` records the user message before calling the AI service.
2. Truncated history (last 50 messages or 10,000 tokens) is injected into the prompt context.
3. The assistant response is recorded after the AI service returns.
4. The conversation's `last_activity` is updated with each message.

---

## Scenario 2: Session Restoration with History Preserved

Close the browser, restore the session, and continue the conversation with full history.

```bash
# Step 1: Have an active conversation (from Scenario 1)
# Session cookie: va_session_id=sess-xyz (stored in cookies.txt)

# Step 2: Simulate session expiry, then restore
curl -X POST http://localhost:5001/session/restore \
  -H "Content-Type: application/json" \
  -d '{"session_id": "sess-xyz"}' \
  -c cookies.txt

# Response:
# {
#   "message": "Session restored successfully",
#   "session_id": "sess-xyz",
#   "current_image_id": "abc-123",
#   "conversation_topic": null
# }

# Step 3: Continue chatting -- history is still available
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What was the first thing you noticed?", "image_id": "abc-123"}' \
  -b cookies.txt -c cookies.txt

# The assistant has access to the full conversation history from before
# the session was restored, because history is tied to conversation_id
# (not just the session's active state).
```

**Key point**: Conversation history persists independently of session expiry. Session restoration reconnects the user to their existing conversations via the session_id index.

---

## Scenario 3: Retrieve Conversation History

Use the `GET /chat/history` endpoint to view past conversations.

```bash
# Get history for a specific image
curl -X GET "http://localhost:5001/chat/history?image_id=abc-123" \
  -b cookies.txt

# Response:
# {
#   "conversations": [
#     {
#       "conversation_id": "conv-001",
#       "image_id": "abc-123",
#       "session_id": "sess-xyz",
#       "created_at": "2026-02-16T10:00:00Z",
#       "last_activity": "2026-02-16T10:05:30Z",
#       "messages": [
#         {"message_id": "msg-001", "role": "user", "content": "What do you see?", ...},
#         {"message_id": "msg-002", "role": "assistant", "content": "I see a landscape...", ...},
#         {"message_id": "msg-003", "role": "user", "content": "Tell me more about the colors", ...},
#         {"message_id": "msg-004", "role": "assistant", "content": "The image has a rich...", ...}
#       ]
#     }
#   ],
#   "count": 1
# }

# Get history for a session (all conversations)
curl -X GET "http://localhost:5001/chat/history?session_id=sess-xyz" \
  -b cookies.txt

# Get history with both filters (AND logic) and a limit
curl -X GET "http://localhost:5001/chat/history?image_id=abc-123&session_id=sess-xyz&limit=5" \
  -b cookies.txt
```

---

## Scenario 4: Streaming with History Context

Use the streaming endpoint with full history context injection.

```bash
# First message (establishes conversation)
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Describe this photo in detail", "image_id": "abc-123"}' \
  -b cookies.txt -c cookies.txt

# Follow-up via streaming (history from first exchange is injected)
curl -N -X POST http://localhost:5001/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Now focus on the lighting", "image_id": "abc-123"}' \
  -b cookies.txt

# Output: SSE stream with history-aware response
# data: {"id":"chatcmpl-...","choices":[{"delta":{"content":"Based on"}}],...}
# data: {"id":"chatcmpl-...","choices":[{"delta":{"content":" our earlier"}}],...}
# data: {"id":"chatcmpl-...","choices":[{"delta":{"content":" discussion"}}],...}
# ...
# data: [DONE]
```

**What happens internally**:
1. The user message is recorded before streaming begins.
2. History context is injected into the prompt sent to the AI service.
3. The stream generator wraps the inner generator to capture the full response text.
4. After the stream completes (or the client disconnects), the full assistant response is recorded to history.

---

## Scenario 5: Automatic Cleanup Behavior

Conversations are automatically cleaned up based on the retention policy.

```
Timeline:
  Day 0:    Conversation created, messages exchanged
  Day 1-29: Conversation accessible normally
  Day 30:   Conversation marked as "stale" (last_activity > 30 days ago)
  Day 30-36: Grace period -- conversation still accessible
  Day 37:   Next hourly cleanup permanently deletes the conversation and its messages
```

**Configuration** (in `config.py`):
```python
HISTORY_RETENTION_DAYS = 30          # Mark stale after 30 days of inactivity
HISTORY_GRACE_PERIOD_DAYS = 7        # 7-day grace before permanent deletion
HISTORY_CLEANUP_INTERVAL_SECONDS = 3600  # Cleanup runs every hour
```

**Behavior**:
- The cleanup service runs as a daemon background thread (starts with the app).
- It iterates all conversations and deletes those exceeding `retention_days + grace_period_days` (37 days by default).
- Cleanup errors are logged but never crash the application.
- Active conversations (with recent `last_activity`) are never affected.

---

## Edge Cases

### Empty History

```bash
# Request history for an image with no conversations
curl -X GET "http://localhost:5001/chat/history?image_id=nonexistent-id"

# Response: empty result set (not an error)
# {"conversations": [], "count": 0}
```

### Missing Required Parameters

```bash
# No filter parameters provided
curl -X GET "http://localhost:5001/chat/history"

# Response: 400 error
# {
#   "error": {
#     "message": "At least one of image_id or session_id is required",
#     "type": "invalid_request_error",
#     "param": null,
#     "code": "missing_filter"
#   }
# }
```

### Concurrent Access

Multiple clients can chat about the same image simultaneously. Thread safety is guaranteed by `threading.RLock`:

```bash
# Terminal 1: User A chats about image abc-123
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is the subject?", "image_id": "abc-123"}' \
  -b cookies_a.txt -c cookies_a.txt

# Terminal 2: User B chats about the same image (different session)
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Describe the colors", "image_id": "abc-123"}' \
  -b cookies_b.txt -c cookies_b.txt

# Each user gets their own conversation with independent history.
# Both conversations reference the same image_id.
# GET /chat/history?image_id=abc-123 returns both conversations.
```

### Graceful Degradation

If the history service encounters an error (e.g., unexpected exception during message recording), the chat request still completes successfully:

```bash
# Even if history recording fails internally, the user gets a normal response
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What do you see?", "image_id": "abc-123"}' \
  -b cookies.txt -c cookies.txt

# Response: 200 OK with normal chat completion
# Server logs: WARNING - "Failed to record user message: <error details>"

# The chat works; history may be incomplete for this exchange.
# Subsequent messages will attempt recording again normally.
```

This ensures that a bug or transient issue in the history subsystem never degrades the core chat experience.
