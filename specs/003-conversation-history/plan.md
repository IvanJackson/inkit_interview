# Implementation Plan: Conversation History

**Branch**: `003-conversation-history` | **Date**: 2026-02-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-conversation-history/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement conversation history storage and retrieval to enable multi-turn conversations with context. The system will store user messages and assistant responses, persist history across sessions, provide history retrieval endpoints, and implement automatic cleanup of old conversations. Initial implementation uses thread-safe in-memory storage with plans for database persistence in Question 4.

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: Flask ≥2.0, threading (built-in for RLock), Pillow (existing), Flask-Limiter (existing), Werkzeug ≥2.0 (existing)
**Storage**: In-memory with thread-safe access (dict + threading.RLock), Database persistence deferred to Question 4
**Testing**: pytest (existing test infrastructure)
**Target Platform**: Linux server (Flask backend API)
**Project Type**: Single backend API (extends existing Q1/Q2 implementation)
**Performance Goals**: History retrieval <500ms for 50 messages, streaming responses start <200ms (maintain existing performance), cleanup runs hourly without blocking requests
**Constraints**: Thread-safe concurrent access, 50,000 char/message limit, 10,000 token context window for AI, graceful degradation on history storage failures
**Scale/Scope**: Multiple concurrent users, ~50 messages per typical conversation, 30-day retention + 7-day grace period

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: RESTful API Design
**Status**: ✓ PASS
**Evidence**: New GET /chat/history endpoint follows REST conventions. Existing POST /chat and POST /chat/stream endpoints enhanced with history context. All endpoints return proper status codes, validate inputs, handle errors gracefully.

### Principle II: OpenAI API Compatibility
**Status**: ✓ PASS
**Evidence**: Conversation history formatted as messages array matching OpenAI API spec. History integrated into chat completion requests transparently. No changes to response formats - maintains exact OpenAI compatibility.

### Principle III: Streaming-First for User Experience
**Status**: ✓ PASS
**Evidence**: Both streaming (POST /chat/stream) and non-streaming (POST /chat) endpoints support history context. No degradation to streaming performance. History retrieval optimized for <500ms response time.

### Principle IV: Concurrent Request Handling
**Status**: ✓ PASS
**Evidence**: Thread-safe storage using threading.RLock (matches existing SessionService pattern). No race conditions in history read/write operations. Supports multiple simultaneous conversations. Cleanup runs in background without blocking user requests.

### Principle V: Security & Validation
**Status**: ✓ PASS
**Evidence**: All history inputs validated (50,000 char/message limit). Unicode/emoji sanitization applied. Rate limiting applies to all endpoints including new /chat/history. No sensitive data in history responses. Automatic cleanup prevents unbounded storage growth.

**Overall**: ✅ ALL GATES PASSED - No violations. Feature fully aligned with constitution principles.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── models/
│   ├── conversation.py          # NEW - Conversation entity (dataclass)
│   ├── message.py                # NEW - Message entity (dataclass)
│   ├── image.py                  # EXISTING
│   ├── session.py                # EXISTING
│   ├── chat.py                   # EXISTING
│   └── response.py               # EXISTING
├── services/
│   ├── conversation_service.py   # NEW - Thread-safe history storage/retrieval
│   ├── image_service.py          # EXISTING
│   ├── session_service.py        # EXISTING
│   ├── chat_service.py           # MODIFY - Add history parameter
│   └── mock_openai_service.py    # MODIFY - Accept history in chat methods
├── api/
│   ├── history.py                # NEW - GET /chat/history endpoint
│   ├── chat.py                   # MODIFY - Integrate history context
│   ├── upload.py                 # MODIFY - Create conversation on upload
│   └── middleware.py             # EXISTING
└── utils/
    ├── logger.py                 # EXISTING
    ├── security.py               # EXISTING
    └── openai_formatter.py       # EXISTING

tests/
├── unit/
│   ├── test_conversation_service.py  # NEW
│   ├── test_history_endpoints.py     # NEW
│   └── [existing test files]
├── integration/
│   └── test_history_integration.py   # NEW
└── concurrent/
    └── test_concurrent_history.py    # NEW

app.py                            # MODIFY - Register history blueprint, start cleanup thread
config.py                         # MODIFY - Add history retention config
```

**Structure Decision**: Single backend API project. This feature extends the existing Q1/Q2 implementation without architectural changes. New conversation history components follow established patterns:
- Models defined as dataclasses (matches existing `session.py`, `chat.py`)
- Thread-safe service with RLock (matches `SessionService` pattern)
- Blueprint-based API routes (matches existing `upload.py`, `chat.py`)
- Test organization by type (unit/integration/concurrent)

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No violations detected.** All constitution principles are satisfied by this implementation plan.
