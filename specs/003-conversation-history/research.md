# Research: Conversation History

**Feature**: 003-conversation-history
**Date**: 2026-02-16
**Status**: Complete

## Overview

This document captures research decisions for implementing conversation history to support multi-turn dialogues in the Visual Assistant API. The design follows existing codebase patterns (SessionService, ImageService) and prioritizes thread safety, graceful degradation, and minimal coupling.

## Decision 1: Storage Strategy

### Decision: Thread-safe nested dictionaries with `threading.RLock`

**Rationale**: The existing codebase already uses this pattern successfully in `SessionService` (`src/services/session_service.py`), which stores sessions in `Dict[str, SessionContext]` protected by `threading.RLock`. Reusing this pattern ensures consistency, avoids introducing new dependencies, and aligns with the constitution's requirement for in-memory storage during initial development (Technical Requirements, Database & Persistence).

**Alternatives Considered**:
- **SQLite**: Provides persistence but adds complexity and a new dependency not present in the current stack. Deferred to Question 4 (production persistence) per the Progressive Enhancement principle.
- **Redis**: Overkill for a single-process Flask dev server. Adds external infrastructure requirements.
- **`collections.OrderedDict`**: Offers insertion-order iteration but lacks built-in thread safety. Would still require RLock wrapping and offers marginal benefit over plain dicts with explicit timestamp fields.

**Data Structures**:
```python
# Primary storage
_conversations: Dict[str, Conversation]          # conversation_id -> Conversation
_messages: Dict[str, List[Message]]              # conversation_id -> [Message, ...]

# Lookup indexes
_conversations_by_image: Dict[str, List[str]]    # image_id -> [conversation_id, ...]
_conversations_by_session: Dict[str, List[str]]  # session_id -> [conversation_id, ...]

# Single RLock protects all four dictionaries
_lock: threading.RLock
```

## Decision 2: Context Truncation

### Decision: Last 50 messages or 10,000 tokens (whichever is reached first)

**Rationale**: OpenAI models have finite context windows. Injecting unbounded history into prompts would eventually exceed token limits and degrade response quality. The 50-message / 10,000-token cap provides sufficient context for meaningful multi-turn conversations while staying well within typical model limits (GPT-4 Vision supports 128K tokens, but practical prompt engineering keeps context focused).

**Token Estimation**: Tokens are estimated as `word_count * 2` (a rough but serviceable heuristic matching the existing pattern in `mock_openai_service.py` lines 119-120). This avoids adding a tokenizer dependency while remaining close enough for truncation decisions.

**Truncation Algorithm**:
1. Retrieve all messages for the conversation, ordered by `created_at` ascending.
2. Iterate from the most recent message backward.
3. Accumulate `token_count` until either 50 messages or 10,000 tokens is reached.
4. Return the selected messages in chronological order.

**Alternatives Considered**:
- **Sliding window by time**: Penalizes slow conversations where early context is still relevant.
- **Summarization**: Requires an additional AI call per request, adding latency and complexity. Could be a future enhancement.
- **No truncation**: Risk of unbounded memory growth and prompt overflow.

## Decision 3: Cleanup Strategy

### Decision: Hourly background thread (`threading.Timer`, `daemon=True`) with 30-day retention + 7-day grace period

**Rationale**: Conversations accumulate over time and must be pruned to prevent unbounded memory growth. A daemon background thread matches the single-process Flask dev server model, requires no external scheduler (cron, Celery), and terminates automatically when the main process exits.

**Retention Policy**:
- **30-day retention**: Conversations with `last_activity` older than 30 days are marked for cleanup.
- **7-day grace period**: After marking, conversations remain accessible for 7 additional days before permanent deletion. This mirrors the `SessionService` pattern of moving expired sessions to `_expired_sessions` before final removal.
- **Hourly interval**: Balances cleanup frequency against CPU overhead. Each cleanup pass iterates all conversations once.

**Implementation**:
```python
class HistoryCleanupService:
    def __init__(self, history_service, retention_days=30, grace_period_days=7, interval_seconds=3600):
        self._history_service = history_service
        self._retention_days = retention_days
        self._grace_period_days = grace_period_days
        self._interval = interval_seconds
        self._timer = None

    def start(self):
        """Start the recurring cleanup timer (daemon thread)."""
        self._schedule_next()

    def _schedule_next(self):
        self._timer = threading.Timer(self._interval, self._run_cleanup)
        self._timer.daemon = True
        self._timer.start()

    def _run_cleanup(self):
        try:
            self._history_service.cleanup_old_conversations(
                self._retention_days, self._grace_period_days
            )
        except Exception:
            logger.exception("History cleanup failed")
        finally:
            self._schedule_next()
```

**Alternatives Considered**:
- **APScheduler**: Full-featured but adds a dependency for a single recurring task.
- **Manual cleanup on request**: Creates unpredictable latency spikes on user-facing endpoints.
- **No cleanup**: Unbounded memory growth. Unacceptable for any deployment duration.

## Decision 4: Thread Safety

### Decision: Reuse RLock pattern from existing services

**Rationale**: The `SessionService` demonstrates a proven pattern: a single `threading.RLock` protecting all mutable state, acquired via `with self._lock:` context manager. This ensures:
- **Reentrancy**: RLock (vs Lock) allows the same thread to acquire the lock multiple times without deadlock, which is necessary when internal methods call each other.
- **Atomicity**: Composite operations (e.g., creating a conversation and updating the index) happen within a single lock acquisition.
- **Simplicity**: One lock per service instance avoids lock-ordering bugs that arise with multiple fine-grained locks.

**Performance Note**: For the target scale (single dev server, <100 concurrent users), a single RLock introduces negligible contention. If scaling requires it, the lock can be replaced with per-conversation locks or migrated to a database with row-level locking (Question 4).

## Decision 5: Integration with Existing Chat Endpoints

### Decision: Extend existing `/chat` and `/chat/stream` to record messages and inject history

**Rationale**: Rather than creating separate "history-aware" endpoints, the existing `POST /chat` and `POST /chat/stream` endpoints in `src/api/chat.py` will be modified to:

1. **Record user messages**: After validating the prompt, save the user's message to the conversation history.
2. **Inject history context**: Before calling `mock_openai_chat()`, retrieve truncated history and prepend it to the prompt context.
3. **Record assistant responses**: After receiving the response (or after streaming completes), save the assistant's message to history.

This approach maintains backward compatibility (existing clients see no breaking changes) and follows the constitution's Progressive Enhancement principle.

**Integration Points in `src/api/chat.py`**:
- `chat()` function (line ~170): Insert history recording around the `mock_openai_chat()` call.
- `chat_stream()` function (line ~267): Wrap the stream generator to capture the full response for recording after stream completion.

## Decision 6: New Endpoint for History Retrieval

### Decision: `GET /chat/history` with query params (`image_id`, `session_id`)

**Rationale**: A dedicated read-only endpoint for history retrieval follows RESTful conventions (GET for reads) and keeps the existing POST endpoints focused on chat interactions. Query parameters allow flexible filtering without requiring separate endpoints per filter type.

**Query Parameters**:
| Parameter    | Type   | Required | Description                              |
|-------------|--------|----------|------------------------------------------|
| `image_id`  | UUID   | No       | Filter conversations by image             |
| `session_id`| UUID   | No       | Filter conversations by session           |
| `limit`     | int    | No       | Max conversations to return (default: 20) |

At least one of `image_id` or `session_id` must be provided. If both are provided, results are filtered by both (AND logic).

**Response Format**:
```json
{
    "conversations": [
        {
            "conversation_id": "uuid",
            "image_id": "uuid",
            "session_id": "uuid",
            "created_at": "ISO8601",
            "last_activity": "ISO8601",
            "messages": [
                {
                    "message_id": "uuid",
                    "role": "user",
                    "content": "What do you see?",
                    "created_at": "ISO8601",
                    "token_count": 8
                }
            ]
        }
    ],
    "count": 1
}
```

## Decision 7: Error Handling Strategy

### Decision: Graceful degradation -- log errors, never fail chat requests

**Rationale**: Conversation history is a supplementary feature that enhances the chat experience but is not essential to its core function. If history recording or retrieval fails (e.g., due to a bug, memory pressure, or lock contention timeout), the chat request should still proceed normally. This matches the constitution's Error Handling standards: "Handle all failure modes gracefully."

**Implementation**:
- All history operations are wrapped in try/except blocks.
- Failures are logged at WARNING or ERROR level using the existing `src/utils/logger.py` module.
- The chat response is returned regardless of history operation success.
- The `/chat/history` GET endpoint returns appropriate error responses (400, 500) since it is a dedicated history endpoint where failure is meaningful to the caller.

```python
# Example: graceful degradation in chat endpoint
try:
    history_service.record_message(conversation_id, role="user", content=prompt)
except Exception:
    logger.warning("Failed to record user message", exc_info=True)

# Chat proceeds normally regardless
chat_response = mock_openai_chat(prompt, image_id, ...)
```

## Summary of Technology Choices

| Concern              | Decision                                      | Matches Existing Pattern |
|----------------------|-----------------------------------------------|-------------------------|
| Storage              | In-memory dicts with RLock                    | SessionService           |
| Token estimation     | `word_count * 2`                              | mock_openai_service      |
| Truncation           | Last 50 messages / 10,000 tokens              | New                      |
| Cleanup              | Daemon `threading.Timer`, hourly              | New (similar to session expiry) |
| Thread safety        | Single `threading.RLock` per service          | SessionService           |
| Integration          | Modify existing endpoints                     | Progressive Enhancement  |
| New endpoint         | `GET /chat/history`                           | RESTful convention       |
| Error handling       | Log and continue                              | Constitution principle   |
