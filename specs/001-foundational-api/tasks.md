# Tasks: Foundational API - Image Upload and Basic Chat

**Input**: Design documents from `/specs/001-foundational-api/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included per constitution requirement ("All endpoints MUST have unit tests").

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths follow the structure defined in plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependency installation, and base structure

- [x] T001 Create project directory structure: `src/models/`, `src/services/`, `src/api/`, `src/utils/`, `tests/unit/`, `tests/integration/`, `tests/concurrent/` with `__init__.py` files
- [x] T002 Add Pillow and flask-limiter to Pipfile and requirements.txt, run `pipenv install`
- [x] T003 [P] Create application configuration in `config.py` with upload limits (16MB, 4096x4096), rate limits (20/hr upload, 100/min chat, 1000/hr global), session timeout (24h), allowed extensions, and prompt length limit (10,000 chars)
- [x] T004 [P] Create Flask app factory in `app.py` with blueprint registration, error handlers, and threaded mode configuration

**Checkpoint**: Project structure created, dependencies installed, configuration ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Implement OpenAI response formatter in `src/utils/openai_formatter.py` — helper functions to build chat completion responses with all required fields (id with "chatcmpl-" prefix, object "chat.completion", created timestamp, model "gpt-4-vision-preview", choices array with message/finish_reason, usage stats). Reference: research.md Section 1 and contracts/openapi.yaml ChatCompletionResponse schema
- [x] T006 [P] Implement OpenAI error formatter in `src/utils/openai_formatter.py` — helper function to build error responses matching OpenAI format (error.message, error.type, error.param, error.code). Reference: research.md Section 8 and contracts/openapi.yaml ErrorResponse schema
- [x] T007 [P] Implement input validation and security utilities in `src/utils/security.py` — functions for XSS/injection detection, Unicode text sanitization, prompt length validation (max 10,000 chars), and filename sanitization. Reference: FR-026, FR-027, SC-018
- [x] T008 Implement error handling middleware in `src/api/middleware.py` — Flask error handlers for 400, 404, 413, 415, 422, 423, 429, 500 that return OpenAI-formatted error responses. Wire up Flask-Limiter with rate limits from config.py. Reference: FR-014, FR-039, research.md Section 6
- [x] T009 Implement Response model in `src/models/response.py` — dataclasses for ChatCompletionResponse, Choice, Message, Usage matching OpenAI format. Reference: data-model.md Entity 5
- [x] T010 Write unit tests for OpenAI formatter and security utilities in `tests/unit/test_openai_formatter.py` and `tests/unit/test_security.py` — verify response format compliance (FR-041 through FR-048) and injection/XSS detection (SC-018)

**Checkpoint**: Foundation ready — OpenAI format helpers, security utilities, error handling, and rate limiting all operational. User story implementation can now begin.

---

## Phase 3: User Story 1 - Upload Image and Get Visual Analysis (Priority: P1) 🎯 MVP

**Goal**: Users can upload image files and receive an immediate AI-powered visual analysis. Multi-layer validation ensures only valid images are accepted, with corruption detection and preview confirmation.

**Independent Test**: Upload a valid JPEG via `curl -X POST http://127.0.0.1:5000/upload -F "image=@photo.jpg"` and receive a JSON response with image_id and OpenAI-formatted analysis. Upload invalid files and verify appropriate error codes (415, 413, 422).

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T011 [P] [US1] Write unit tests for Image model in `tests/unit/test_models.py` — test Image creation with all fields, validation of corruption_status enum, preview_data optional field. Reference: data-model.md Entity 1
- [ ] T012 [P] [US1] Write unit tests for image validation service in `tests/unit/test_image_service.py` — test file type validation (JPEG/PNG/GIF/WebP accept, PDF/EXE reject), size validation (≤16MB), dimension validation (≤4096x4096), content validation (magic numbers), metadata extraction, corruption detection. Reference: FR-001 through FR-015, SC-001, SC-005, SC-006, SC-007, SC-013
- [ ] T013 [P] [US1] Write integration tests for upload workflow in `tests/integration/test_upload_workflow.py` — test full upload happy path (valid image → 200 + image_id + analysis), invalid type → 415, oversized → 413, bad dimensions → 422, metadata failure → 422, corruption flow → preview + confirm/reject. Reference: spec.md User Story 1 acceptance scenarios 1-9

### Implementation for User Story 1

- [x] T014 [P] [US1] Create Image model in `src/models/image.py` — dataclass with fields: id (UUID), filename, size_bytes, width, height, format, mode, file_path, uploaded_at, corruption_status ("valid"/"suspected"/"confirmed"), preview_data (optional base64), vision_analysis (optional). Reference: data-model.md Entity 1
- [x] T015 [US1] Implement image validation and processing service in `src/services/image_service.py` — thread-safe ImageService class with RLock-protected image store dict. Methods: validate_file_type() using magic number verification, validate_file_size() (≤16MB), validate_dimensions() using Pillow (≤4096x4096), extract_metadata() (dimensions/format/mode), detect_corruption() using Pillow verify(), generate_preview() (base64 thumbnail for corrupted images), save_image() (to uploads/ with UUID filename), add_image()/get_image() with lock. Reference: research.md Section 2, FR-001 through FR-015
- [x] T016 [US1] Implement mock OpenAI vision analysis in `src/services/mock_openai_service.py` — mock_openai_vision_analysis(image_path) function that returns ChatCompletionResponse with mock description of the image. Use openai_formatter helpers. Include simulated delay (0.1s). Reference: FR-041, FR-043, FR-047, research.md Section 1
- [x] T017 [US1] Implement upload endpoint in `src/api/upload.py` — Flask blueprint with POST /upload route. Accept multipart/form-data, run full validation pipeline (type → size → content → metadata → dimensions → corruption), call vision analysis on success, return image_id + metadata + analysis. Handle corruption flow: return 422 with preview_base64 and confirmation_url. Apply rate limit (20/hr). Reference: contracts/openapi.yaml POST /upload
- [x] T018 [US1] Implement upload confirmation endpoint in `src/api/upload.py` — POST /upload/confirm route. Accept {image_id, action: "confirm_valid"/"confirm_corrupted"}. If valid: run vision analysis and return result. If corrupted: return re-upload prompt. Reference: contracts/openapi.yaml POST /upload/confirm, FR-008, FR-009
- [x] T019 [US1] Register upload blueprint in `app.py` and verify end-to-end upload workflow works with `curl`

**Checkpoint**: User Story 1 fully functional — images can be uploaded with full validation, corruption detection with preview, and OpenAI-formatted vision analysis. Run `tests/unit/test_image_service.py` and `tests/integration/test_upload_workflow.py` to verify.

---

## Phase 4: User Story 2 - Ask Questions About Uploaded Images (Priority: P2)

**Goal**: Users can ask natural language questions about uploaded images with ChatGPT-like UX — session-based context (no image IDs needed), silly excuse generation during uploads with request queuing, photo relevance analysis for conversation continuity, and session persistence across disconnections.

**Independent Test**: Upload an image, then `curl -X POST http://127.0.0.1:5000/chat -H "Content-Type: application/json" -d '{"prompt": "What do you see?"}'` — should respond referencing the uploaded image without specifying image_id. Test silly excuse by chatting during upload. Test session restore after disconnect.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T020 [P] [US2] Write unit tests for Session and ChatRequest models in `tests/unit/test_models.py` — test SessionContext creation/expiry/restoration, ChatRequest with/without explicit image_id, QueuedRequest lifecycle. Reference: data-model.md Entities 2-4
- [ ] T021 [P] [US2] Write unit tests for session service in `tests/unit/test_session_service.py` — test session creation, get/update with lock, expiry detection (24h), persistence of expired sessions, restoration, browser tab isolation (different browser_device_id → different session), device switch requiring re-auth. Reference: FR-018, FR-019, FR-033 through FR-037, SC-010, SC-011
- [ ] T022 [P] [US2] Write unit tests for chat service in `tests/unit/test_chat_service.py` — test image resolution (session default vs explicit override), upload-in-progress detection, silly excuse generation (random from list), request queuing, queue processing on upload complete, photo relevance analysis (related vs unrelated mock), prompt validation (length, sanitization). Reference: FR-016 through FR-032, SC-003, SC-007, SC-008, SC-009
- [ ] T023 [P] [US2] Write integration tests for chat workflow in `tests/integration/test_chat_workflow.py` — test full flow: upload → chat without image_id → correct response, chat before upload → 400 error, explicit image_id override, prompt too long → 400. Reference: spec.md User Story 2 acceptance scenarios 1-2, 7, 12-15
- [ ] T024 [P] [US2] Write integration tests for queuing workflow in `tests/integration/test_queuing_workflow.py` — test chat during upload → 202 + silly excuse + queued, poll queue_id → 202 pending, upload completes → queued request auto-processed, poll queue_id → 200 with response, poll non-existent queue_id → 404. Reference: spec.md User Story 2 acceptance scenarios 3-4, FR-024a through FR-024d, SC-007, SC-008
- [ ] T025 [P] [US2] Write integration tests for session persistence in `tests/integration/test_session_persistence.py` — test session expiry → restore → continue conversation, device switch → require re-auth, browser tab isolation. Reference: spec.md User Story 2 acceptance scenarios 9-11, SC-010, SC-011

### Implementation for User Story 2

- [ ] T026 [P] [US2] Create SessionContext model in `src/models/session.py` — dataclass with fields: session_id (UUID), current_image_id (optional), conversation_topic (optional, max 500 chars), browser_device_id, created_at, last_activity, authenticated (bool), expired (bool). Reference: data-model.md Entity 2
- [ ] T027 [P] [US2] Create ChatRequest and QueuedRequest models in `src/models/chat.py` — ChatRequest dataclass with id, session_id, image_id (optional override), prompt (1-10,000 chars), created_at, queue_status ("immediate"/"queued"). QueuedRequest dataclass with id, chat_request, upload_image_id, queued_at, session_id. Reference: data-model.md Entities 3-4
- [ ] T028 [US2] Implement session management service in `src/services/session_service.py` — thread-safe SessionService class with RLock-protected session store and expired_sessions store. Methods: create_session(), get_session() with expiry check, update_session() (touch last_activity), get_or_create_session() from request cookies/headers, persist_expired_session(), restore_session() from expired store, validate_device() for re-auth check, generate_browser_device_id() from User-Agent + headers. Session timeout: 24h. Reference: research.md Section 3, FR-018, FR-019, FR-033 through FR-037
- [ ] T029 [US2] Implement chat processing service in `src/services/chat_service.py` — ChatService class. Methods: resolve_image_id() (check explicit → session default → error), check_upload_in_progress(), generate_silly_excuse() (random from list: "I went to the bathroom", "I'm fetching the dog", "I'm making coffee", "I stepped out for fresh air", "I'm watering the plants"), queue_request(), process_queued_requests() (called on upload completion), analyze_photo_relevance() (mock heuristic: compare conversation_topic with new image features, return related/unrelated). Reference: research.md Sections 4-5, FR-020 through FR-031
- [ ] T030 [US2] Implement mock OpenAI chat completion in `src/services/mock_openai_service.py` — add mock_openai_chat(prompt, image_id, stream=False) function that returns non-streaming ChatCompletionResponse with mock answer. Include simulated delay (0.2s). Format silly excuses and photo relevance prompts as chat completions. Reference: FR-042, FR-044 through FR-050, research.md Section 1
- [ ] T031 [US2] Implement session middleware in `src/api/middleware.py` — add before_request hook to extract/create session from cookies, attach to Flask g. Add after_request hook to set session cookie. Generate browser_device_id for tab isolation. Reference: FR-018, FR-033
- [ ] T032 [US2] Implement chat endpoint in `src/api/chat.py` — Flask blueprint with POST /chat route. Extract prompt and optional image_id from JSON body. Validate prompt (length, sanitization via security.py). Resolve image via session or explicit ID. If upload in progress: return 202 with silly excuse + queue request. If no image: return 400 "Please upload an image first". Normal flow: call mock_openai_chat, return response. Apply rate limit (100/min). Reference: contracts/openapi.yaml POST /chat
- [ ] T033 [US2] Implement photo relevance endpoint in `src/api/chat.py` — POST /chat/relevance route. Accept {action: "start_new"/"keep_current", new_image_id}. If start_new: update session.current_image_id. If keep_current: no change. Return confirmation message. Reference: contracts/openapi.yaml POST /chat/relevance, FR-028 through FR-030
- [ ] T034 [US2] Implement session restore endpoint in `src/api/chat.py` — POST /session/restore route. Accept {session_id, auth_token (optional)}. Validate device match, require re-auth if different. Restore session from expired store. Return session context. Reference: contracts/openapi.yaml POST /session/restore, FR-034 through FR-037
- [ ] T034b [US2] Implement queue polling endpoint in `src/api/chat.py` — GET /chat/queue/{queue_id} route. Return 202 + "pending" if still waiting, 200 + full ChatCompletionResponse if processed, 404 if queue_id not found. Reference: contracts/openapi.yaml GET /chat/queue/{queue_id}, FR-024a through FR-024d
- [ ] T035 [US2] Wire upload completion callback in `src/services/image_service.py` — after successful upload and vision analysis, call chat_service.process_queued_requests(image_id) to auto-process any queued chat requests and store results for polling retrieval. Reference: FR-024, SC-008
- [ ] T036 [US2] Wire photo relevance check into upload endpoint in `src/api/upload.py` — after successful upload, if session has existing conversation_topic, call analyze_photo_relevance(). If unrelated, include relevance prompt in response. Reference: FR-028, FR-029
- [ ] T037 [US2] Register chat blueprint in `app.py` and verify end-to-end chat workflow with `curl`

**Checkpoint**: User Story 2 fully functional — natural chat UX with session context, silly excuses during upload, request queuing, photo relevance analysis, session persistence and restoration. Run all US2 tests to verify.

---

## Phase 5: User Story 3 - Reliable Multi-User API Access (Priority: P3)

**Goal**: System handles production-like concurrent workloads with zero data corruption, complete session isolation, and graceful rate limiting under load.

**Independent Test**: Run 10+ concurrent upload and chat requests using threading. Verify zero errors, no response mixing, correct session isolation, and rate limiting responses under burst load.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T038 [P] [US3] Write concurrent upload tests in `tests/concurrent/test_concurrent_uploads.py` — spawn 10+ threads each uploading different images simultaneously, verify all succeed with unique image_ids, no data corruption. Reference: SC-002, SC-014
- [ ] T039 [P] [US3] Write concurrent chat tests in `tests/concurrent/test_concurrent_chats.py` — spawn 10+ threads each chatting about different images in separate sessions, verify correct responses per session, no cross-contamination. Reference: SC-004, SC-014
- [ ] T040 [P] [US3] Write session isolation tests in `tests/concurrent/test_session_isolation.py` — simulate multiple browser tabs (different sessions) uploading and chatting simultaneously, verify complete context isolation. Reference: SC-011, FR-033
- [ ] T041 [P] [US3] Write rate limiting tests in `tests/unit/test_rate_limiting.py` — verify upload rate limit (>20/hr → 429), chat rate limit (>100/min → 429), global IP limit (>1000/hr → 429), Retry-After header present. Reference: plan.md rate limiting section

### Implementation for User Story 3

- [ ] T042 [US3] Audit and harden thread safety across all services in `src/services/` — verify all shared state dictionaries (image_store, session_store, expired_sessions, queued_requests, upload_status) use RLock consistently. Add missing locks if any. Verify no race conditions in upload → queue processing → chat response pipeline. Reference: research.md Section 7, FR-013, FR-032, SC-014
- [ ] T043 [US3] Verify rate limiting configuration in `src/api/middleware.py` — confirm Flask-Limiter decorators applied to all endpoints with correct limits. Test 429 responses include Retry-After header. Verify rate limiting works per-session (not just per-IP) for upload and chat endpoints. Reference: plan.md Principle V compliance
- [ ] T044 [US3] Add graceful degradation under load in `src/api/middleware.py` — ensure system returns 429 with helpful message rather than crashing when overwhelmed. Add request timeout handling for long-running operations. Reference: spec.md User Story 3 acceptance scenario 4

**Checkpoint**: System handles 10+ concurrent users with zero data corruption, complete session isolation, and graceful rate limiting. Run `tests/concurrent/` to verify.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final hardening, documentation, and validation across all stories

- [ ] T045 [P] Add comprehensive logging across all services in `src/services/` — log upload attempts (success/failure/corruption), chat requests, session lifecycle events, queue operations, rate limit hits. Never log sensitive data (file contents, user prompts). Reference: constitution Development Standards
- [ ] T046 [P] Add security warnings for cookie/device switching in chat responses via `src/services/session_service.py` — include warning header or response field when session is accessed from unfamiliar context. Reference: FR-036
- [ ] T047 [P] Validate all response formats against OpenAI specification — run through every endpoint and response type (vision analysis, chat completion, silly excuse, photo relevance, error), verify exact field match with contracts/openapi.yaml. Reference: SC-012, FR-047
- [ ] T048 Code cleanup and refactoring — review all files for clear naming, proper separation of concerns, no hardcoded values (use config.py), comprehensive docstrings for public functions, type hints. Reference: constitution Code Quality standards
- [ ] T049 Run quickstart.md validation — execute every curl command from `specs/001-foundational-api/quickstart.md` and verify responses match documented examples
- [ ] T050 Final full test suite run — execute `pipenv run pytest tests/ -v` and verify 100% pass rate across unit, integration, and concurrent tests

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — can start immediately after Phase 2
- **User Story 2 (Phase 4)**: Depends on Foundational AND User Story 1 (needs upload endpoint and image service for chat to reference images)
- **User Story 3 (Phase 5)**: Depends on User Story 1 AND User Story 2 (tests concurrent access across both features)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories. This IS the MVP.
- **User Story 2 (P2)**: Depends on User Story 1 — needs Image model, image_service, upload endpoint, and mock_openai_service as foundation for chat functionality
- **User Story 3 (P3)**: Depends on User Story 1 AND User Story 2 — tests concurrent access across both upload and chat features simultaneously

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**:
- T003 and T004 can run in parallel

**Phase 2 (Foundational)**:
- T005 and T007 can run in parallel (different files)
- T006 can run with T007 (different functions in different files)
- T009 can run with T007 (different files)
- T010 runs after T005, T006, T007

**Phase 3 (US1)**:
- T011, T012, T013 can ALL run in parallel (test files)
- T014 can run in parallel with tests (model file)
- T017 and T018 are sequential (same file, different routes)

**Phase 4 (US2)**:
- T020, T021, T022, T023, T024, T025 can ALL run in parallel (test files)
- T026 and T027 can run in parallel (different model files)
- T032, T033, T034 are sequential (same blueprint file)

**Phase 5 (US3)**:
- T038, T039, T040, T041 can ALL run in parallel (test files)

**Phase 6 (Polish)**:
- T045, T046, T047 can ALL run in parallel (different concerns)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Write unit tests for Image model in tests/unit/test_models.py"          # T011
Task: "Write unit tests for image validation in tests/unit/test_image_service.py"  # T012
Task: "Write integration tests for upload in tests/integration/test_upload_workflow.py"  # T013

# Launch model in parallel with tests:
Task: "Create Image model in src/models/image.py"  # T014

# Then sequential implementation:
Task: "Implement image validation service in src/services/image_service.py"  # T015
Task: "Implement mock vision analysis in src/services/mock_openai_service.py"  # T016
Task: "Implement upload endpoint in src/api/upload.py"  # T017
Task: "Implement upload confirm endpoint in src/api/upload.py"  # T018
```

## Parallel Example: User Story 2

```bash
# Launch all tests for User Story 2 together:
Task: "Write unit tests for Session/Chat models in tests/unit/test_models.py"  # T020
Task: "Write unit tests for session service in tests/unit/test_session_service.py"  # T021
Task: "Write unit tests for chat service in tests/unit/test_chat_service.py"  # T022
Task: "Write integration tests for chat in tests/integration/test_chat_workflow.py"  # T023
Task: "Write integration tests for queuing in tests/integration/test_queuing_workflow.py"  # T024
Task: "Write integration tests for session persistence in tests/integration/test_session_persistence.py"  # T025

# Launch models in parallel:
Task: "Create SessionContext model in src/models/session.py"  # T026
Task: "Create ChatRequest/QueuedRequest models in src/models/chat.py"  # T027
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T010)
3. Complete Phase 3: User Story 1 (T011-T019)
4. **STOP and VALIDATE**: Upload images, verify analysis, test error cases
5. Deploy/demo: Working image upload with full validation and OpenAI-formatted responses

### Incremental Delivery

1. Setup + Foundational → Foundation ready (T001-T010)
2. Add User Story 1 → Test independently → Deploy/Demo (MVP! Image upload works)
3. Add User Story 2 → Test independently → Deploy/Demo (Chat UX with session context, silly excuses, queuing)
4. Add User Story 3 → Test independently → Deploy/Demo (Production-ready concurrent handling)
5. Polish → Final hardening → Full release

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (MVP — must complete first)
   - Developer B: User Story 2 tests (T020-T025, can write while A implements US1)
3. After US1 complete:
   - Developer A: User Story 3
   - Developer B: User Story 2 implementation (T026-T037)
4. Both complete → Polish phase together

---

## Summary

| Metric | Count |
|--------|-------|
| **Total Tasks** | 51 |
| **Phase 1 (Setup)** | 4 tasks |
| **Phase 2 (Foundational)** | 6 tasks |
| **Phase 3 (US1 - Upload)** | 9 tasks (3 test + 6 implementation) |
| **Phase 4 (US2 - Chat)** | 19 tasks (6 test + 13 implementation) |
| **Phase 5 (US3 - Concurrent)** | 7 tasks (4 test + 3 implementation) |
| **Phase 6 (Polish)** | 6 tasks |
| **Parallel Opportunities** | 28 tasks can run in parallel |
| **MVP Scope** | T001-T019 (19 tasks for working image upload) |

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
