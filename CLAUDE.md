# candidate_files Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-14

## Active Technologies
- Python 3.13 (project uses 3.13; constitution requires 3.8+ compatibility) + Flask >=2.0 (existing), Flask-Limiter (existing), Pillow (existing) (002-streaming-responses)
- In-memory (Phase 1 — no new storage needed for streaming) (002-streaming-responses)
- Python 3.13 + Flask ≥2.0, threading (built-in for RLock), Pillow (existing), Flask-Limiter (existing), Werkzeug ≥2.0 (existing) (003-conversation-history)
- In-memory with thread-safe access (dict + threading.RLock), Database persistence deferred to Question 4 (003-conversation-history)

- Python 3.13 + Flask ≥2.0, Werkzeug ≥2.0 (for secure file handling), Pillow (for image validation/metadata), Flask-Limiter (for rate limiting) (001-foundational-api)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.13: Follow standard conventions

## Recent Changes
- 003-conversation-history: Added Python 3.13 + Flask ≥2.0, threading (built-in for RLock), Pillow (existing), Flask-Limiter (existing), Werkzeug ≥2.0 (existing)
- 003-conversation-history: Added [if applicable, e.g., PostgreSQL, CoreData, files or N/A]
- 002-streaming-responses: Added Python 3.13 (project uses 3.13; constitution requires 3.8+ compatibility) + Flask >=2.0 (existing), Flask-Limiter (existing), Pillow (existing)


<!-- MANUAL ADDITIONS START -->

## Conversation History Feature

### Overview
The Visual Assistant API maintains multi-turn conversation history, allowing users to have coherent back-and-forth exchanges about uploaded images without repeating context.

### Key Features
- **Multi-turn conversations**: AI remembers previous messages in the conversation
- **Session persistence**: History survives session changes (conversations tied to images, not sessions)
- **Context truncation**: Last 50 messages or 10,000 tokens (whichever limit reached first)
- **Automatic cleanup**: Conversations older than 30 days (+ 7-day grace period) are automatically deleted
- **Graceful degradation**: History failures don't block chat requests

### API Endpoints

#### POST /upload
Upload an image and optionally start a conversation immediately:

```bash
# Upload only (creates conversation for future chat)
curl -X POST http://localhost:5001/upload \
  -F "image=@photo.jpg"

# Upload + immediate chat (hybrid approach)
curl -X POST http://localhost:5001/upload \
  -F "image=@photo.jpg" \
  -F "prompt=What colors do you see?"
```

Response includes `image_id` and optional `chat_response` (if prompt provided).

#### POST /chat
Chat about the current image with history context:

```bash
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=YOUR_SESSION_ID" \
  -d '{"prompt": "Are they warm or cool?"}'
```

The AI receives the last 50 messages (or 10,000 tokens) as context, so it understands "they" refers to previously mentioned colors.

#### POST /chat/stream
Same as /chat but streams the response via Server-Sent Events (SSE):

```bash
curl -X POST http://localhost:5001/chat/stream \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=YOUR_SESSION_ID" \
  -d '{"prompt": "Describe the composition"}' \
  --no-buffer
```

#### GET /chat/history
Retrieve conversation history for transparency/reference:

```bash
# Get history by image_id
curl "http://localhost:5001/chat/history?image_id=550e8400-e29b-41d4-a716-446655440000"

# Get history by session_id
curl "http://localhost:5001/chat/history?session_id=6ba7b810-9dad-11d1-80b4-00c04fd430c8"

# Get history with limit
curl "http://localhost:5001/chat/history?image_id=550e8400-e29b-41d4-a716-446655440000&limit=10"
```

Response format:
```json
{
  "conversations": [
    {
      "conversation_id": "conv-uuid",
      "image_id": "img-uuid",
      "session_id": "sess-uuid",
      "created_at": "2026-02-16T10:00:00Z",
      "last_activity": "2026-02-16T10:05:30Z",
      "messages": [
        {
          "message_id": "msg-uuid",
          "role": "user",
          "content": "What colors do you see?",
          "created_at": "2026-02-16T10:00:00Z",
          "token_count": 10
        },
        {
          "message_id": "msg-uuid",
          "role": "assistant",
          "content": "I see warm tones...",
          "created_at": "2026-02-16T10:00:02Z",
          "token_count": 50
        }
      ]
    }
  ],
  "count": 1
}
```

### Configuration

In `config.py`:
```python
HISTORY_RETENTION_DAYS = 30          # Delete conversations older than this
HISTORY_GRACE_PERIOD_DAYS = 7        # Keep active conversations extra days
HISTORY_CLEANUP_INTERVAL_SECONDS = 3600  # Run cleanup every hour
HISTORY_MAX_MESSAGES = 50            # Max messages in AI context
HISTORY_MAX_TOKENS = 10_000          # Max tokens in AI context
```

### Implementation Details

- **Storage**: In-memory dictionaries with thread-safe access (threading.RLock)
- **Indexes**: Four dictionaries for fast lookup by conversation_id, image_id, session_id, messages
- **Primary key**: Conversations use `image_id` as primary lookup (enables session persistence)
- **Cleanup**: Background daemon thread runs hourly to delete old conversations
- **Error handling**: All service operations wrapped in try/except with graceful fallbacks

### Streaming Quality Improvements (Feb 2026)

When conversation history was added (Q3), the streaming endpoint was modified to capture and store assistant responses. During this integration, two critical streaming features from Q2 were inadvertently lost. These have since been restored:

#### 1. Backpressure Handling (Priority 1 Fix)
**Problem**: Without backpressure control, the server could overwhelm slow clients by generating chunks faster than they could consume them, leading to buffering issues and potential memory exhaustion.

**Solution**: Added buffer tracking in `guarded_stream()` (src/api/chat.py:386-391):
- Tracks number of buffered chunks (threshold: 10 chunks)
- Adds 10ms delay when buffer exceeds threshold
- Prevents server from overwhelming slow consumers
- Maintains streaming responsiveness for normal clients

**Why it matters**: Ensures stable streaming connections even with varying client speeds (slow network, slow parsing, mobile devices).

#### 2. Reconnection Support (Priority 2 Fix)
**Problem**: If a client's connection dropped mid-stream (network hiccup, mobile switching WiFi/cellular), they had no way to resume from where they left off. They'd have to restart and receive duplicate content.

**Solution**: Implemented SSE standard reconnection (src/api/chat.py:337-365):
- Generates unique event IDs for each chunk: `conv-{conversation_id}-{event_number}`
- Supports `Last-Event-ID` header (SSE standard)
- Skips already-sent events when client reconnects
- Client sends `Last-Event-ID: conv-abc-123-42` → server resumes from event 43

**Why it matters**: Mobile clients and unstable networks can gracefully resume streams without data loss or duplication.

#### 3. Full Content Capture (Priority 3 Fix)
**Problem**: Streaming responses were being stored in history as `"[Streamed response]"` placeholder instead of the actual message content, making conversation history incomplete.

**Solution**: Added delta chunk parsing and reconstruction (src/api/chat.py:353-362):
- Parses each SSE chunk to extract content deltas
- Reconstructs full message by joining all content fragments
- Stores actual assistant response in history
- Falls back to placeholder only if reconstruction fails

**Why it matters**: Conversation history now accurately reflects what was said, enabling proper context for follow-up questions.

### Testing the Streaming Fixes

```bash
# Test backpressure (slow client simulation)
curl -N -X POST http://localhost:5001/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a long story", "image_id": "abc-123"}' \
  -b cookies.txt | while read line; do sleep 0.1; echo "$line"; done

# Test reconnection (capture event ID, then reconnect from it)
curl -N -X POST http://localhost:5001/chat/stream \
  -H "Content-Type: application/json" \
  -H "Last-Event-ID: conv-f47ac10b-58cc-4372-a567-0e02b2c3d479-5" \
  -d '{"prompt": "Continue story", "image_id": "abc-123"}' \
  -b cookies.txt

# Verify content capture (check history shows full message, not placeholder)
curl "http://localhost:5001/chat/history?image_id=abc-123" | jq '.conversations[0].messages[-1].content'
```

<!-- MANUAL ADDITIONS END -->
