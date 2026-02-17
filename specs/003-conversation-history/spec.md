# Feature Specification: Conversation History

**Feature Branch**: `003-conversation-history`
**Created**: 2026-02-16
**Status**: Draft
**Input**: User description: "Implement conversation history storage and retrieval. The system should maintain multi-turn conversation context, allowing users to have coherent back-and-forth exchanges with the AI about their uploaded images. Conversations should persist across sessions, support message history retrieval, and include cleanup mechanisms for old conversations. Users should be able to view their conversation history and continue where they left off."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Store and Retrieve Conversation Context (Priority: P1)

Users can have multi-turn conversations about their uploaded images, with each message building on the previous context. The assistant remembers what was discussed previously and provides coherent, contextually-aware responses.

**Why this priority**: This is the core value of conversation history - enabling natural, multi-turn dialogues. Without this, users must repeat context in every message. This is the MVP that delivers immediate user value.

**Independent Test**: Upload an image, ask "What colors do you see?", then ask "Are they warm or cool?" without re-specifying the image. The assistant should understand "they" refers to the previously mentioned colors and respond appropriately based on conversation context.

**Acceptance Scenarios**:

1. **Given** a user has uploaded an image and received vision analysis, **When** they ask a follow-up question referencing previous context (e.g., "tell me more about that"), **Then** the assistant provides a relevant response based on the full conversation history
2. **Given** a user asks multiple questions in sequence, **When** they ask "what did I just ask about?", **Then** the assistant can reference the previous message in the conversation
3. **Given** a user has a 5-message conversation about an image, **When** they ask a new question, **Then** the system includes all previous messages as context for the AI response
4. **Given** a conversation exists for an image, **When** a user asks a question via streaming or non-streaming endpoint, **Then** both endpoints include conversation history in the response generation

---

### User Story 2 - Persist History Across Sessions (Priority: P2)

Users can close their browser, return hours or days later, and continue their conversation exactly where they left off. The conversation history persists beyond the current session lifetime.

**Why this priority**: Extends the value of conversation history beyond a single session. Users often need to pause and resume analysis of their images. This enables long-term, asynchronous collaboration with the AI assistant.

**Independent Test**: Start a conversation about an image (3 messages), close the browser completely, clear cookies, reopen the browser, upload the same image or restore session, and verify the previous 3 messages are visible and inform the next AI response.

**Acceptance Scenarios**:

1. **Given** a user has a 3-message conversation and their session expires, **When** they restore their session, **Then** the full conversation history is available and visible
2. **Given** a user uploaded an image yesterday and had a conversation, **When** they return today with the same session, **Then** they can view the complete conversation history from yesterday
3. **Given** a user has multiple images with different conversations, **When** they switch between images, **Then** each image displays its own independent conversation history
4. **Given** a user's session cookie is lost but they have the image_id, **When** they provide the image_id in a chat request, **Then** the conversation history for that image is retrieved and used for context

---

### User Story 3 - View and Navigate Conversation History (Priority: P3)

Users can view their entire conversation history for an image, including timestamps, message roles (user vs assistant), and the full content of each message. This provides transparency and enables users to reference earlier parts of long conversations.

**Why this priority**: Enhances usability for users with long conversations. While context is automatically provided to the AI (P1), users also benefit from seeing their conversation timeline visually. This is polish that improves UX but isn't required for basic functionality.

**Independent Test**: Have a 10-message conversation, then call a new endpoint `/chat/history` with the session or image_id, and verify it returns a chronological list of all 10 messages with timestamps, roles, and content.

**Acceptance Scenarios**:

1. **Given** a user has a conversation with 10 messages, **When** they request the conversation history, **Then** they receive all 10 messages in chronological order with timestamps and role labels (user/assistant)
2. **Given** a conversation spans multiple days, **When** history is retrieved, **Then** messages are grouped or labeled by date for easier navigation
3. **Given** a user has both streaming and non-streaming messages in their history, **When** they view history, **Then** all messages appear regardless of how they were delivered
4. **Given** a user requests history for an image with no conversation, **When** the request is made, **Then** an empty history array is returned (not an error)

---

### User Story 4 - Automatic History Cleanup (Priority: P3)

Old conversation histories are automatically removed after a configurable retention period to prevent unbounded storage growth. Users are notified when their history will expire, and cleanup happens gracefully without impacting active conversations.

**Why this priority**: Operational necessity for production systems, but doesn't impact core user experience. Can be implemented after the feature is functional and validated. Important for long-term sustainability but not for initial launch.

**Independent Test**: Configure history retention to 7 days, create a conversation, manually advance system time by 8 days (or wait in staging), verify the conversation history is automatically deleted and no longer retrievable.

**Acceptance Scenarios**:

1. **Given** history retention is set to 30 days and a conversation is 31 days old, **When** the cleanup process runs, **Then** the conversation history is removed from storage
2. **Given** a conversation has some messages older than the retention period and some newer, **When** cleanup runs, **Then** only messages older than the retention threshold are removed
3. **Given** a user has an active conversation (message within last 24 hours), **When** cleanup runs, **Then** the conversation is not deleted regardless of the age of the first message
4. **Given** history cleanup is running, **When** a user tries to send a message, **Then** their message is processed without delay or error
5. **Given** a conversation will expire soon, **When** a user requests history, **Then** the response includes the expiration date (optional enhancement)

---

### Edge Cases

- What happens when a user has two browser tabs open for the same image and sends messages from both tabs simultaneously?
- How does the system handle a conversation history retrieval request while a streaming response is still in progress?
- What happens if conversation history storage fails mid-request (disk full, database error)?
- How does the system handle Unicode, emoji, and special characters in conversation history?
- What happens when a user references a deleted image in their conversation history?
- How does history integrate with the existing "photo relevance" flow where users switch image context?
- What happens if history retrieval times out or fails - does the chat request still succeed without context?
- How does the system handle very long conversations (100+ messages) - is there a pagination or truncation strategy?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store every user message and assistant response as part of the conversation history for the associated image/session
- **FR-002**: System MUST include conversation history as context when generating AI responses (both streaming and non-streaming)
- **FR-003**: System MUST persist conversation history beyond the session lifetime (survives browser close, session expiration)
- **FR-004**: System MUST associate conversation history with images via image_id or session_id
- **FR-005**: System MUST handle concurrent access to conversation history (multiple messages in flight, multiple tabs)
- **FR-006**: System MUST provide an endpoint to retrieve conversation history for an image/session
- **FR-007**: System MUST return conversation history in chronological order with timestamps
- **FR-008**: System MUST include message role (user or assistant) and content in history records
- **FR-009**: System MUST store history for both streaming and non-streaming chat responses
- **FR-010**: System MUST implement automatic cleanup of conversation history older than a configurable retention period (default: 30 days)
- **FR-011**: System MUST not delete conversations that have had activity within the retention grace period (default: 7 days from last message)
- **FR-012**: System MUST handle history storage failures gracefully (log error, continue request without failing)
- **FR-013**: System MUST support Unicode, emoji, and special characters in conversation history
- **FR-014**: System MUST limit the size of individual history records (e.g., max 50,000 characters per message)
- **FR-015**: System MUST truncate or paginate conversation history when providing context to AI if history exceeds a reasonable token limit (e.g., 10,000 tokens)
- **FR-016**: System MUST return empty history (not an error) when retrieving history for an image with no conversation
- **FR-017**: Cleanup process MUST run asynchronously and not block or delay user requests
- **FR-018**: System MUST maintain separate conversation histories for different images
- **FR-019**: System MUST preserve conversation history when sessions are restored
- **FR-020**: System MUST include conversation history in the context passed to `mock_openai_chat` for both streaming and non-streaming modes

### Key Entities

- **Conversation**: Represents the full history of messages for a specific image or session
  - Attributes: conversation_id (unique identifier), image_id (associated image), session_id (associated session), created_at (first message timestamp), last_activity (most recent message timestamp)
  - Relationships: Contains multiple Messages

- **Message**: Represents a single turn in the conversation (user prompt or assistant response)
  - Attributes: message_id (unique identifier), conversation_id (parent conversation), role (user or assistant), content (message text), created_at (timestamp), token_count (optional - for context truncation)
  - Relationships: Belongs to one Conversation

- **HistoryRetentionPolicy**: Configuration for automatic cleanup
  - Attributes: retention_days (how long to keep history), grace_period_days (activity threshold to prevent deletion)
  - Note: This may be a configuration value rather than a stored entity

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can have multi-turn conversations where follow-up questions correctly reference previous context without re-explaining
- **SC-002**: Conversation history persists across session restoration - users can resume conversations after browser restart
- **SC-003**: System handles concurrent history writes (e.g., multiple tabs sending messages) without data loss or corruption
- **SC-004**: History retrieval completes in under 500ms for conversations with up to 50 messages
- **SC-005**: System continues to accept chat requests even when history storage fails (degrades gracefully)
- **SC-006**: Conversation history cleanup runs automatically and removes histories older than the configured retention period without manual intervention
- **SC-007**: Both streaming and non-streaming chat endpoints produce contextually-aware responses using conversation history
- **SC-008**: Users can retrieve their full conversation history and see all past messages with accurate timestamps and role labels

## Assumptions *(document reasonable defaults)*

1. **Storage mechanism**: In-memory storage is acceptable for initial implementation (Question 4 will add database persistence). History will be lost on server restart in this phase.
2. **Retention period**: Default history retention is 30 days, with a 7-day grace period for active conversations. This is configurable but follows industry standards for free-tier conversation storage.
3. **Context truncation**: If a conversation exceeds ~10,000 tokens (approximately 40-50 messages), older messages are truncated when providing context to the AI. This prevents exceeding typical LLM context windows.
4. **Concurrency**: History storage uses thread-safe data structures (locks or thread-safe collections) to handle concurrent access from multiple requests or tabs.
5. **Message size**: Individual messages are limited to 50,000 characters to prevent storage abuse. This is well beyond typical conversational messages.
6. **History scope**: Conversation history is tied to image_id primarily, with session_id as a secondary key for session restoration scenarios.
7. **Cleanup frequency**: Automatic cleanup runs once per hour (configurable). This is sufficient for production without excessive overhead.
8. **Frontend**: The browser UI displays conversation history automatically by rendering all messages in the chat area. No separate history panel is required initially.
9. **Error handling**: If history retrieval fails, the chat request continues with empty context rather than failing the request. History storage failures are logged but don't block responses.
10. **Unicode support**: Full Unicode (including emoji) is supported in conversation history, consistent with existing chat input validation.
