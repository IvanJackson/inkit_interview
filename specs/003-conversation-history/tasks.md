---
description: "Task list for Conversation History feature implementation"
---

# Tasks: Conversation History

**Input**: Design documents from `/specs/003-conversation-history/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL for this feature. No explicit test requirements found in spec.md, so implementation tasks focus on core functionality with manual validation per quickstart.md scenarios.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Project Type**: Single backend API (extends existing Q1/Q2 implementation)
- **Structure**: `src/`, `tests/` at repository root
- All paths shown below use this structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Configuration and project setup for conversation history

- [X] T001 Add history retention configuration to config.py (HISTORY_RETENTION_DAYS=30, HISTORY_GRACE_PERIOD_DAYS=7, HISTORY_CLEANUP_INTERVAL_SECONDS=3600, HISTORY_MAX_MESSAGES=50, HISTORY_MAX_TOKENS=10000)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

**Status**: ✅ ALL FOUNDATIONAL WORK EXISTS
- Existing infrastructure from Q1/Q2 provides all prerequisites:
  - Database schema: In-memory storage ready (SessionService pattern established)
  - Authentication/authorization: Session management working
  - API routing: Flask blueprints configured
  - Base models: Image, Session, Chat models exist
  - Error handling: Logging infrastructure ready
  - Configuration: Config.py pattern established

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Store and Retrieve Conversation Context (Priority: P1) 🎯 MVP

**Goal**: Enable multi-turn conversations where the AI remembers previous context. Users can ask follow-up questions without repeating context.

**Independent Test**: Upload an image, ask "What colors do you see?", then ask "Are they warm or cool?" without re-specifying the image. The assistant should understand "they" refers to the previously mentioned colors and respond appropriately based on conversation context.

### Implementation for User Story 1

- [X] T002 [P] [US1] Create Conversation dataclass model in src/models/conversation.py (conversation_id, session_id, image_id, created_at, last_activity, touch() method)
- [X] T003 [P] [US1] Create Message dataclass model in src/models/message.py (message_id, conversation_id, role, content, created_at, token_count, validation in __post_init__)
- [X] T004 [US1] Create ConversationService in src/services/conversation_service.py (thread-safe storage with RLock, _conversations dict, _messages dict, _conversations_by_image index, _conversations_by_session index, get_or_create_conversation(), add_message(), get_messages(), get_context_for_ai() with truncation)
- [X] T005 [US1] Modify ChatService.chat() in src/services/chat_service.py to accept optional history parameter and pass to mock_openai_chat
- [X] T006 [US1] Modify ChatService.stream_chat() in src/services/chat_service.py to accept optional history parameter and pass to mock_openai_chat for streaming
- [X] T007 [US1] Modify mock_openai_chat() in src/services/mock_openai_service.py to accept optional history parameter and prepend history messages to prompt context (format as messages array per OpenAI API)
- [X] T008 [US1] Modify POST /upload endpoint in src/api/upload.py to create conversation via conversation_service.get_or_create_conversation(image_id, session_id) after successful upload
- [X] T009 [US1] Modify POST /chat endpoint in src/api/chat.py to retrieve history, add user message, generate response with history context, add assistant message (graceful degradation on history failures per FR-012)
- [X] T010 [US1] Modify POST /chat/stream endpoint in src/api/chat.py to retrieve history, add user message, stream response with history context, add assistant message after stream completes (graceful degradation on history failures)
- [X] T011 [US1] Register conversation_service singleton instance in app.py and pass to chat blueprint

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Test with quickstart.md Scenario 1 (Multi-turn conversation).

---

## Phase 4: User Story 2 - Persist History Across Sessions (Priority: P2)

**Goal**: Conversation history persists beyond session lifetime. Users can close browser, return later, and continue where they left off.

**Independent Test**: Start a conversation about an image (3 messages), close the browser completely, clear cookies, reopen the browser, upload the same image or restore session, and verify the previous 3 messages are visible and inform the next AI response.

### Implementation for User Story 2

- [X] T012 [US2] Add session restoration history lookup in src/services/conversation_service.py (get_or_create_conversation already handles this - lookup by image_id retrieves existing conversation regardless of session changes, per Decision 4 in research.md)
- [X] T013 [US2] Verify conversation history lookup by image_id works when session_id changes in ConversationService (review get_or_create_conversation implementation, ensure image_id is primary key as designed)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Test with quickstart.md Scenario 2 (Session restoration).

---

## Phase 5: User Story 3 - View and Navigate Conversation History (Priority: P3)

**Goal**: Users can retrieve their full conversation history with timestamps, roles, and content for transparency and reference.

**Independent Test**: Have a 10-message conversation, then call GET /chat/history with the session or image_id, and verify it returns a chronological list of all 10 messages with timestamps, roles, and content.

### Implementation for User Story 3

- [X] T014 [P] [US3] Create GET /chat/history endpoint in src/api/history.py (query parameters: image_id, session_id, limit; return conversations with messages in HistoryResponse format per contracts/openapi.yaml; validate at least one filter provided; handle empty history gracefully per FR-016)
- [X] T015 [US3] Register history blueprint in app.py with url_prefix='/chat'

**Checkpoint**: All core user stories (US1, US2, US3) should now be independently functional. Test with quickstart.md Scenario 3 (History retrieval).

---

## Phase 6: User Story 4 - Automatic History Cleanup (Priority: P3)

**Goal**: Automatically remove old conversation histories after configurable retention period to prevent unbounded storage growth.

**Independent Test**: Configure history retention to 7 days, create a conversation, manually advance system time by 8 days (or wait in staging), verify the conversation history is automatically deleted and no longer retrievable.

### Implementation for User Story 4

- [X] T016 [US4] Implement cleanup_old_conversations() method in src/services/conversation_service.py (iterate _conversations, calculate age from last_activity, delete if older than retention_days + grace_period_days, remove from all indexes, log cleanup summary)
- [X] T017 [US4] Implement start_cleanup_thread() function in src/services/conversation_service.py (create daemon thread, run cleanup_old_conversations() every HISTORY_CLEANUP_INTERVAL_SECONDS in a loop with error handling)
- [X] T018 [US4] Start cleanup background thread in app.py after creating conversation_service singleton (call start_cleanup_thread(conversation_service) before app.run())

**Checkpoint**: All user stories (US1-US4) should now be complete. Test with quickstart.md Scenario 5 (Cleanup simulation) if possible.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and overall quality

- [X] T019 [P] Add comprehensive error handling and logging for all conversation service operations (wrap all RLock operations with try/except, log errors with context)
- [X] T020 [P] Add input validation for message content length (50,000 char limit per FR-014) in ConversationService.add_message()
- [X] T021 [P] Add Unicode/emoji support validation in Message model (ensure content handles UTF-8 properly per FR-013)
- [X] T022 Performance test: Verify history retrieval <500ms for 50 messages (measure get_context_for_ai() execution time, optimize if needed per SC-004)
- [X] T023 Concurrency test: Verify thread-safe operations with multiple simultaneous chat requests (simulate multiple tabs sending messages, verify no data corruption per SC-003, FR-005)
- [X] T024 Graceful degradation test: Verify chat requests succeed when history operations fail (mock history_service failures, ensure chat continues per FR-012, SC-005)
- [X] T025 Context truncation test: Verify conversations exceeding 50 messages or 10,000 tokens are truncated correctly (create long conversation, verify get_context_for_ai() returns last 50 messages or 10,000 tokens per FR-015)
- [X] T026 [P] Update CLAUDE.md documentation with conversation history usage examples
- [X] T027 Run quickstart.md validation for all 5 scenarios (multi-turn conversation, session restoration, history retrieval, concurrent access, cleanup simulation)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Already complete from Q1/Q2 - No blocking work
- **User Stories (Phase 3-6)**: All depend on Setup (Phase 1) completion
  - User stories can proceed in parallel (if staffed) or sequentially in priority order (P1 → P2 → P3 → P3)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Setup (Phase 1) - No dependencies on other stories
- **User Story 2 (P2)**: Depends on US1 completion (needs ConversationService) - Uses existing get_or_create_conversation logic
- **User Story 3 (P3)**: Depends on US1 completion (needs ConversationService) - Independent GET endpoint
- **User Story 4 (P3)**: Depends on US1 completion (needs ConversationService) - Independent cleanup thread

### Within Each User Story

- **US1 (P1)**:
  1. Models (T002, T003) can run in parallel [P]
  2. Service (T004) depends on models
  3. Service modifications (T005, T006, T007) depend on T004 (ConversationService exists)
  4. Endpoint modifications (T008, T009, T010) depend on service modifications
  5. App registration (T011) depends on all above

- **US2 (P2)**:
  1. Review/verification tasks (T012, T013) can run after US1 complete

- **US3 (P3)**:
  1. Endpoint creation (T014) depends on US1 (ConversationService exists)
  2. Registration (T015) depends on T014

- **US4 (P3)**:
  1. Cleanup methods (T016, T017) depend on US1 (ConversationService exists)
  2. Thread start (T018) depends on cleanup methods

### Parallel Opportunities

- **Phase 1 Setup**: Only 1 task (T001) - no parallelization
- **Phase 3 US1**:
  - T002 and T003 can run in parallel [P] (different models)
  - T005, T006, T007 can run in parallel [P] after T004 (different service files)
- **Phase 7 Polish**:
  - T019, T020, T021, T026 can run in parallel [P] (different files or independent changes)
  - Tests (T022-T025) should run sequentially as they validate integrated behavior

---

## Parallel Example: User Story 1

```bash
# After T001 (config) completes, launch models in parallel:
Task Agent A: "Create Conversation dataclass model in src/models/conversation.py"
Task Agent B: "Create Message dataclass model in src/models/message.py"

# After T002-T003 and T004 complete, launch service modifications in parallel:
Task Agent A: "Modify ChatService.chat() in src/services/chat_service.py"
Task Agent B: "Modify ChatService.stream_chat() in src/services/chat_service.py"
Task Agent C: "Modify mock_openai_chat() in src/services/mock_openai_service.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Skip Phase 2: Foundational (already done in Q1/Q2)
3. Complete Phase 3: User Story 1 (T002-T011)
4. **STOP and VALIDATE**: Test User Story 1 independently with quickstart.md Scenario 1
5. Deploy/demo if ready - this is the MVP!

### Incremental Delivery

1. Complete Setup (T001) → Configuration ready
2. Add User Story 1 (T002-T011) → Test independently → Deploy/Demo (MVP! Multi-turn conversations working)
3. Add User Story 2 (T012-T013) → Test independently → Deploy/Demo (Session persistence working)
4. Add User Story 3 (T014-T015) → Test independently → Deploy/Demo (History retrieval API working)
5. Add User Story 4 (T016-T018) → Test independently → Deploy/Demo (Automatic cleanup working)
6. Polish (T019-T027) → Final validation and optimization

Each story adds value without breaking previous stories.

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup (Phase 1) together
2. Team completes User Story 1 (Phase 3) together - this is the critical MVP path
3. Once US1 is done and validated:
   - Developer A: User Story 2 (session persistence)
   - Developer B: User Story 3 (history API)
   - Developer C: User Story 4 (cleanup)
4. Stories complete and integrate independently
5. Team reconvenes for Polish phase

---

## Notes

- **[P] tasks** = different files, no dependencies - can run in parallel
- **[Story] label** maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **Graceful degradation**: History failures MUST NOT block chat requests (FR-012, SC-005)
- **Thread safety**: All ConversationService operations protected by threading.RLock (matches SessionService pattern from Q1/Q2)
- **Context truncation**: Last 50 messages OR 10,000 tokens, whichever limit reached first (FR-015)
- **Cleanup frequency**: Hourly background thread, 30-day retention + 7-day grace period (FR-010, FR-011, FR-017)
- **Storage indexes**: Four dicts (conversations, messages, by_image, by_session) all protected by same RLock
- **Primary key**: conversation_id uses image_id as basis for cross-session continuity (Decision 4 in research.md)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- Validate with quickstart.md scenarios as each story completes

---

## Task Summary

- **Total Tasks**: 27
- **Setup Tasks**: 1 (T001)
- **Foundational Tasks**: 0 (inherited from Q1/Q2)
- **User Story 1 Tasks**: 10 (T002-T011) - MVP
- **User Story 2 Tasks**: 2 (T012-T013)
- **User Story 3 Tasks**: 2 (T014-T015)
- **User Story 4 Tasks**: 3 (T016-T018)
- **Polish Tasks**: 9 (T019-T027)

**Parallel Opportunities**: 7 tasks marked [P] across all phases

**Independent Test Criteria**:
- **US1**: Multi-turn conversation with context retention
- **US2**: Session persistence across browser restart
- **US3**: History retrieval API returns all messages
- **US4**: Automatic cleanup removes old conversations

**Suggested MVP Scope**: Phase 1 (Setup) + Phase 3 (User Story 1) = 11 tasks
