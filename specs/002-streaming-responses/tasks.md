# Tasks: Streaming Chat Responses

**Input**: Design documents from `/specs/002-streaming-responses/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included — the constitution requires testing for all endpoints and streaming format validation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add streaming configuration and shared utilities that all user stories depend on

- [X] T001 Add streaming configuration values (MAX_STREAMING_CONNECTIONS=50, STREAM_TIMEOUT_SECONDS=30) to config.py
- [X] T002 [P] Add 503 error handler for streaming capacity exceeded in app.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core streaming formatters and mock service — MUST be complete before any user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Implement format_stream_chunk() function in src/utils/openai_formatter.py (FR-006, FR-007, FR-008)
- [X] T004 Implement format_stream_chunks() generator in src/utils/openai_formatter.py (FR-009 through FR-014)
- [X] T005 Implement streaming mode (stream=True) in mock_openai_chat() in src/services/mock_openai_service.py (FR-022, FR-024, FR-025, FR-026)
- [X] T006 Add _stream_response() helper with per-word delay distribution in src/services/mock_openai_service.py (FR-025)

**Checkpoint**: Streaming formatters and mock service ready — endpoint and frontend work can now begin

---

## Phase 3: User Story 1 — Real-Time Streaming Chat Response (Priority: P1) MVP

**Goal**: Users send a prompt and see the response appear word-by-word in real time via SSE

**Independent Test**: Send a POST to /chat/stream and verify SSE chunks arrive incrementally with correct OpenAI format, reassembled content matches non-streaming response

### Tests for User Story 1

- [X] T007 [P] [US1] Unit tests for format_stream_chunk() — verify chunk structure, delta field, finish_reason, usage in tests/unit/test_streaming.py
- [X] T008 [P] [US1] Unit tests for format_stream_chunks() — verify sequence (role, content, stop, usage, DONE), shared ID, content reassembly in tests/unit/test_streaming.py
- [X] T009 [P] [US1] Endpoint tests for POST /chat/stream — verify content-type, valid SSE chunks, [DONE] termination, 400 on missing prompt in tests/unit/test_streaming.py

### Implementation for User Story 1

- [X] T010 [US1] Implement POST /chat/stream endpoint in src/api/chat.py with prompt validation, rate limiting, and SSE Response (FR-001 through FR-005)
- [X] T011 [US1] Set correct SSE headers (text/event-stream, Cache-Control: no-cache, X-Accel-Buffering: no, Connection: keep-alive) in src/api/chat.py (FR-002, FR-003)
- [X] T012 [US1] Update frontend sendMessage() to use /chat/stream for text-only messages via fetch + ReadableStream in static/index.html
- [X] T013 [US1] Implement addStreamingBubble() for progressive token rendering in static/index.html
- [X] T014 [US1] Verify non-streaming /chat endpoint still works unchanged — run existing tests in tests/unit/ (FR-021, SC-006)

**Checkpoint**: User Story 1 complete — streaming chat works end-to-end, non-streaming endpoint unchanged

---

## Phase 4: User Story 2 — Connection Resilience (Priority: P2)

**Goal**: Server detects client disconnects and stops processing; client falls back to /chat on stream failure

**Independent Test**: Simulate client disconnect mid-stream and verify server stops generating chunks; simulate stream failure and verify client retries via /chat

### Tests for User Story 2

- [X] T015 [P] [US2] Unit test for GeneratorExit handling — verify generator stops cleanly on disconnect in tests/unit/test_streaming.py
- [X] T016 [P] [US2] Unit test for stream timeout — verify generator terminates after STREAM_TIMEOUT_SECONDS in tests/unit/test_streaming.py

### Implementation for User Story 2

- [X] T017 [US2] Add try/except GeneratorExit/finally pattern to _stream_response() in src/services/mock_openai_service.py (FR-015)
- [X] T018 [US2] Add elapsed time tracking and timeout enforcement inside _stream_response() generator loop in src/services/mock_openai_service.py (FR-020)
- [X] T019 [US2] Implement client-side fallback — on stream error, retry via /chat and display full response in static/index.html (FR-016, FR-017)
- [X] T020 [US2] Handle network errors during streaming — display error message and re-enable input controls in static/index.html (FR-017)

**Checkpoint**: User Story 2 complete — server handles disconnects gracefully, client falls back on failure

---

## Phase 5: User Story 3 — Concurrent Streaming Sessions (Priority: P3)

**Goal**: Multiple users stream simultaneously without data mixing or degradation; system enforces connection limits

**Independent Test**: Open 10 concurrent streaming connections and verify each receives its own correct response; open 51st connection and verify 503

### Tests for User Story 3

- [X] T021 [P] [US3] Concurrent streaming test — 10 simultaneous streams, verify no data mixing in tests/unit/test_streaming.py (SC-003)
- [X] T022 [P] [US3] Connection limit test — verify 503 when exceeding MAX_STREAMING_CONNECTIONS in tests/unit/test_streaming.py (FR-018, FR-019)

### Implementation for User Story 3

- [X] T023 [US3] Implement BoundedSemaphore-based connection limiter in src/api/chat.py (FR-018)
- [X] T024 [US3] Add semaphore acquire (non-blocking) before stream and release in generator finally block in src/api/chat.py (FR-018, FR-019)
- [X] T025 [US3] Return 503 with OpenAI error format when at capacity in src/api/chat.py (FR-019)

**Checkpoint**: User Story 3 complete — concurrent streams work correctly, capacity limits enforced

---

## Phase 6: User Story 4 — Backpressure Protection (Priority: P3)

**Goal**: System protects against slow consumers and enforces rate limiting on streaming requests

**Independent Test**: Verify rate-limited streaming request gets 429 before stream begins; verify stream timeout terminates long-running connections

### Tests for User Story 4

- [X] T026 [P] [US4] Rate limit test — verify streaming endpoint returns 429 when rate exceeded in tests/unit/test_streaming.py (SC-007)

### Implementation for User Story 4

- [X] T027 [US4] Verify rate limiting decorator is applied to /chat/stream endpoint (same as /chat) in src/api/chat.py (FR-005, SC-007)
- [X] T028 [US4] Verify timeout from US2 (T018) terminates connections that exceed STREAM_TIMEOUT_SECONDS in src/services/mock_openai_service.py (FR-020)

**Checkpoint**: User Story 4 complete — backpressure mechanisms protect server resources

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, cleanup, and cross-story integration testing

- [X] T029 Run all existing Q1 tests to confirm zero regressions (SC-006)
- [X] T030 Run quickstart.md validation — verify all curl examples work as documented
- [X] T031 [P] Verify streaming response content matches non-streaming response for same input (SC-002, FR-023)
- [X] T032 [P] Verify first token arrives within 200ms in test environment (SC-001)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3–6)**: All depend on Foundational phase completion
  - US1 (Phase 3): Can start after Phase 2
  - US2 (Phase 4): Can start after Phase 2, benefits from US1 endpoint existing
  - US3 (Phase 5): Can start after Phase 2, requires US1 endpoint to test concurrency
  - US4 (Phase 6): Can start after Phase 2, leverages US2 timeout implementation
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: After Phase 2 — no dependencies on other stories
- **US2 (P2)**: After Phase 2 — enhances US1's streaming generator but independently testable
- **US3 (P3)**: After Phase 2 — tests concurrent US1 endpoints but independently implementable
- **US4 (P3)**: After Phase 2 — validates rate limiting applied in US1, timeout from US2

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Formatter/service changes before endpoint changes
- Endpoint changes before frontend changes
- Story complete before moving to next priority

### Parallel Opportunities

- T001 and T002 can run in parallel (Phase 1)
- T003 and T004 can run sequentially (T004 depends on T003), T005–T006 can run in parallel with T003–T004 (different files)
- All [P] tests within a user story can run in parallel
- US3 and US4 can be worked on in parallel (different concerns)

---

## Parallel Example: User Story 1

```bash
# Launch tests in parallel (different test classes):
Task: "Unit tests for format_stream_chunk() in tests/unit/test_streaming.py"
Task: "Unit tests for format_stream_chunks() in tests/unit/test_streaming.py"
Task: "Endpoint tests for POST /chat/stream in tests/unit/test_streaming.py"

# Then implement (sequential — endpoint depends on service):
Task: "Implement POST /chat/stream endpoint in src/api/chat.py"
Task: "Set correct SSE headers in src/api/chat.py"

# Then frontend (different file, can parallel with endpoint verification):
Task: "Update frontend sendMessage() in static/index.html"
Task: "Implement addStreamingBubble() in static/index.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (config values)
2. Complete Phase 2: Foundational (formatters + mock service)
3. Complete Phase 3: User Story 1 (endpoint + frontend)
4. **STOP and VALIDATE**: Test streaming end-to-end, verify non-streaming still works
5. Deploy/demo if ready — users can already see streaming responses

### Incremental Delivery

1. Setup + Foundational → Streaming infrastructure ready
2. Add US1 → Streaming works end-to-end (MVP!)
3. Add US2 → Resilient to connection drops, timeout protection
4. Add US3 → Handles concurrent users, capacity limits
5. Add US4 → Rate limiting and backpressure validated
6. Each story adds robustness without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Existing code already has partial streaming implementation from initial Q2 work — tasks should build on/refactor what exists
- The mock_openai_service.py already has stream parameter support — tasks should enhance with disconnect detection, timeout, and proper error handling
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
