# Implementation Plan: Streaming Chat Responses

**Branch**: `002-streaming-responses` | **Date**: 2026-02-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-streaming-responses/spec.md`

## Summary

Add Server-Sent Events (SSE) streaming to the chat endpoint so users see responses token-by-token in real time. The streaming mock AI service splits responses into word-level chunks matching the OpenAI `chat.completion.chunk` format. Server-side connection management handles client disconnects, concurrent stream limits, and per-connection timeouts. The existing non-streaming `/chat` endpoint remains unchanged. The frontend falls back to `/chat` if streaming fails.

## Technical Context

**Language/Version**: Python 3.13 (project uses 3.13; constitution requires 3.8+ compatibility)
**Primary Dependencies**: Flask >=2.0 (existing), Flask-Limiter (existing), Pillow (existing)
**Storage**: In-memory (Phase 1 — no new storage needed for streaming)
**Testing**: pytest (existing — 62 tests passing)
**Target Platform**: Linux/macOS server, modern web browsers
**Project Type**: Web application (Flask backend + vanilla JS frontend)
**Performance Goals**: First token within 200ms (SC-001), 10 concurrent streams without degradation (SC-003)
**Constraints**: <1s disconnect detection (SC-004), 30s max stream duration (FR-020), 50 max concurrent streams (FR-018)
**Scale/Scope**: Single-server deployment, in-memory state

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: RESTful API Design ✅

- ✅ Streaming endpoint uses POST method with JSON request body
- ✅ Returns proper status codes: 200 (stream), 400 (bad input), 429 (rate limit), 503 (capacity)
- ✅ Validates all inputs before initiating stream
- ✅ Error responses use consistent OpenAI error format (JSON, not SSE)

### Principle II: OpenAI API Compatibility ✅

- ✅ SSE chunks use `chat.completion.chunk` object type with `delta` instead of `message`
- ✅ Required fields: id, object, created, model, choices, usage (FR-007)
- ✅ Event sequence: role → content deltas → stop → usage → [DONE] (FR-009–FR-013)
- ✅ All chunks share same id and created timestamp (FR-014)
- ✅ Mock responses indistinguishable from production OpenAI streaming

### Principle III: Streaming-First for User Experience ✅

- ✅ Core focus of this feature — SSE streaming for chat responses
- ✅ Backpressure: concurrent connection limit (FR-018), per-connection timeout (FR-020)
- ✅ Connection drops: server-side disconnect detection (FR-015), client-side fallback (FR-016)
- ✅ Non-streaming compatibility maintained (FR-021)
- ✅ Concurrent streaming connections supported (FR-018, SC-003)

### Principle IV: Concurrent Request Handling ✅

- ✅ Thread-safe connection counter with locking for concurrent stream tracking
- ✅ Each stream is independent — no shared mutable state between streams
- ✅ Resource cleanup on disconnect/timeout (generator stops, counter decrements)
- ✅ Flask threaded mode handles concurrent requests

### Principle V: Security & Validation ✅

- ✅ Same prompt validation and sanitization as non-streaming endpoint (FR-004)
- ✅ Same rate limiting applied (FR-005)
- ✅ No sensitive data in SSE events or error messages
- ✅ Connection limits prevent resource exhaustion (FR-018)

### Gate Decision: ✅ PROCEED TO PHASE 0 RESEARCH

All constitution principles satisfied. No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/002-streaming-responses/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── api/
│   ├── chat.py              # MODIFY: Add /chat/stream endpoint, streaming connection manager
│   └── middleware.py         # MODIFY: Add streaming connection counter middleware
├── models/
│   └── (no changes)
├── services/
│   └── mock_openai_service.py  # MODIFY: Implement stream=True with generator + disconnect detection
├── utils/
│   └── openai_formatter.py     # MODIFY: Add format_stream_chunk, format_stream_chunks

static/
└── index.html               # MODIFY: Add streaming fetch + fallback logic

config.py                    # MODIFY: Add streaming config (timeout, max connections)

tests/
├── unit/
│   ├── test_streaming.py        # NEW: SSE format, chunk sequence, endpoint tests
│   └── test_openai_formatter.py # EXTEND: Add streaming formatter tests
├── concurrent/
│   └── test_concurrent_streams.py  # NEW: Concurrent streaming tests
└── integration/
    └── (deferred to Phase 4)
```

**Structure Decision**: Extends existing web application structure. No new directories needed — streaming code integrates into existing modules. New test files added under existing test directories.

## Complexity Tracking

No constitution violations. No complexity justification needed.
