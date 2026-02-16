# Feature Specification: Streaming Chat Responses

**Feature Branch**: `002-streaming-responses`
**Created**: 2026-02-16
**Status**: Draft
**Input**: User description: "Implement streaming chat responses using Server-Sent Events (SSE) that match OpenAI API specifications, with connection resilience, backpressure handling, and concurrent streaming support"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Real-Time Streaming Chat Response (Priority: P1)

A user sends a text prompt through the chat interface and sees the assistant's response appear word-by-word in real time, rather than waiting for the entire response to load at once. This provides immediate visual feedback that the system is working and dramatically reduces perceived wait time.

**Why this priority**: This is the core value proposition of streaming. Without it, users stare at a loading spinner for seconds, creating uncertainty about whether the system is processing their request. Streaming provides immediate, continuous feedback.

**Independent Test**: Can be fully tested by sending a chat prompt to the streaming endpoint and verifying that response tokens arrive incrementally before the full response is complete.

**Acceptance Scenarios**:

1. **Given** a user has the chat interface open, **When** they send a text-only prompt, **Then** the response appears token-by-token in the chat bubble as each chunk arrives from the server.
2. **Given** a user sends a prompt, **When** the streaming response begins, **Then** the first token appears within 200ms of the request being sent.
3. **Given** a user sends a prompt to the streaming endpoint, **When** the response completes, **Then** the final assembled text is identical to what a non-streaming request would have returned for the same prompt.
4. **Given** a user sends a prompt, **When** the stream completes, **Then** token usage statistics are included in the final event.

---

### User Story 2 - Connection Resilience (Priority: P2)

A user is receiving a streaming response when their network connection briefly drops (e.g., switching from Wi-Fi to cellular, temporary network hiccup). The system gracefully handles the disconnection on both the server and client side. The client automatically falls back to a non-streaming request to retrieve the complete response.

**Why this priority**: Network instability is common, especially on mobile. Without resilience, users lose partial responses and must re-submit their prompt, leading to frustration and wasted server resources.

**Independent Test**: Can be tested by simulating a client disconnect mid-stream and verifying the server stops processing, and by verifying the client retries or falls back gracefully.

**Acceptance Scenarios**:

1. **Given** a streaming response is in progress, **When** the client disconnects, **Then** the server detects the disconnection and stops generating further chunks within 1 second.
2. **Given** a streaming response fails mid-stream, **When** the client detects the failure, **Then** it automatically retries the request using the non-streaming endpoint as a fallback.
3. **Given** the streaming endpoint is unavailable, **When** the client attempts to connect, **Then** it falls back to the non-streaming `/chat` endpoint and displays the full response normally.

---

### User Story 3 - Concurrent Streaming Sessions (Priority: P3)

Multiple users (or the same user in multiple tabs) are simultaneously receiving streaming responses. The system handles all concurrent streams without mixing up responses, dropping connections, or degrading performance for any individual user.

**Why this priority**: A production-ready system must handle multiple simultaneous users. Without concurrency support, the system would serialize responses or corrupt data across sessions.

**Independent Test**: Can be tested by opening multiple simultaneous streaming connections and verifying each receives its own complete, correct response without interference.

**Acceptance Scenarios**:

1. **Given** 10 users are simultaneously receiving streaming responses, **When** all streams are active, **Then** each user receives their own correct, complete response with no data mixing.
2. **Given** the system is under concurrent streaming load, **When** a new streaming request arrives, **Then** it begins streaming within the normal response time (no queuing delay from other streams).
3. **Given** the maximum number of concurrent streaming connections is reached, **When** a new streaming request arrives, **Then** the system returns an appropriate error indicating capacity has been reached, rather than silently failing.

---

### User Story 4 - Backpressure Protection (Priority: P3)

The system protects itself from being overwhelmed by slow-consuming clients or excessive streaming requests. If a client reads data too slowly, the server does not accumulate unbounded memory. Rate limits apply to streaming requests just as they do to non-streaming requests.

**Why this priority**: Without backpressure handling, a single slow client could cause memory exhaustion on the server, affecting all users.

**Independent Test**: Can be tested by sending streaming requests at a rate exceeding the limit and verifying rate limiting applies, and by simulating a slow consumer and verifying the server does not accumulate unbounded buffered data.

**Acceptance Scenarios**:

1. **Given** a client is consuming streaming data very slowly, **When** the server's output buffer for that connection grows beyond a threshold, **Then** the server terminates the connection rather than accumulating unbounded memory.
2. **Given** streaming requests are rate-limited, **When** a user exceeds the rate limit, **Then** they receive a 429 response before any SSE events are sent.
3. **Given** a streaming connection has been open beyond the maximum allowed duration, **When** the timeout threshold is reached, **Then** the server closes the connection.

---

### Edge Cases

- What happens when the user sends an empty prompt to the streaming endpoint? System returns a 400 error before initiating the stream.
- What happens when a streaming request is made while an image upload is still in progress? System returns a non-streaming error response indicating the upload is not yet complete.
- What happens when the response content is extremely short (e.g., one word)? System still emits the full SSE event sequence: role chunk, content chunk, stop chunk, usage chunk, and done sentinel.
- What happens when the client sends a valid prompt but immediately closes the connection? Server detects the disconnect and stops chunk generation without logging an error.
- What happens when multiple streaming requests arrive from the same session simultaneously? Each request is handled independently with its own stream; responses are not mixed.

## Requirements *(mandatory)*

### Functional Requirements

**Streaming Endpoint**

- **FR-001**: System MUST provide a streaming endpoint that accepts the same request format as the non-streaming chat endpoint (prompt and optional image_id).
- **FR-002**: System MUST return responses using the `text/event-stream` MIME type with `Cache-Control: no-cache` and `Connection: keep-alive` headers.
- **FR-003**: System MUST disable proxy buffering via `X-Accel-Buffering: no` header to prevent reverse proxies from batching SSE events.
- **FR-004**: System MUST validate and sanitize the prompt using the same validation rules as the non-streaming endpoint before initiating the stream.
- **FR-005**: System MUST apply the same rate limiting to the streaming endpoint as the non-streaming chat endpoint.

**SSE Event Format (OpenAI Compatibility)**

- **FR-006**: Each SSE event MUST be formatted as `data: {JSON}\n\n` where JSON matches the OpenAI `chat.completion.chunk` object structure.
- **FR-007**: Each chunk MUST contain: `id` (shared across all chunks in one completion), `object` (always `"chat.completion.chunk"`), `created` (Unix timestamp, shared), `model`, `choices` array, and `usage` (null except on the final usage chunk).
- **FR-008**: Each choice in a chunk MUST contain: `index`, `delta` (instead of `message`), `logprobs`, and `finish_reason`.
- **FR-009**: The first chunk MUST contain a delta with `role: "assistant"` and empty `content: ""` to signal the start of the assistant's response.
- **FR-010**: Content chunks MUST contain a delta with a `content` field holding the incremental text token.
- **FR-011**: The stop chunk MUST contain an empty delta `{}` with `finish_reason: "stop"`.
- **FR-012**: A usage chunk MUST be emitted after the stop chunk, containing `prompt_tokens`, `completion_tokens`, and `total_tokens`.
- **FR-013**: The stream MUST terminate with a `data: [DONE]\n\n` sentinel event.
- **FR-014**: All chunks within a single completion MUST share the same `id` and `created` timestamp.

**Connection Resilience**

- **FR-015**: System MUST detect client disconnections and stop generating further chunks within 1 second of the disconnect.
- **FR-016**: The client MUST automatically fall back to the non-streaming `/chat` endpoint if the streaming endpoint fails or the stream is interrupted mid-response.
- **FR-017**: The client MUST handle network errors during streaming gracefully by displaying an error message and re-enabling the input controls.

**Backpressure and Resource Management**

- **FR-018**: System MUST enforce a maximum number of concurrent streaming connections (configurable, default 50).
- **FR-019**: System MUST return a 503 Service Unavailable response when the concurrent streaming connection limit is reached.
- **FR-020**: System MUST implement a per-connection streaming timeout (configurable, default 30 seconds) after which the stream is terminated.

**Backward Compatibility**

- **FR-021**: The existing non-streaming `/chat` endpoint MUST continue to function identically to its current behavior.
- **FR-022**: The mock AI service MUST support both `stream=True` (returning a generator of SSE chunks) and `stream=False` (returning a complete response dict) through the same function interface.
- **FR-023**: The streaming response, when fully reassembled from all content deltas, MUST produce the same text content as the equivalent non-streaming response for the same input.

**Streaming Mock AI Service**

- **FR-024**: The mock AI service MUST generate streaming responses by splitting the response text into word-level tokens and yielding them as individual SSE chunks.
- **FR-025**: The mock AI service MUST simulate realistic streaming delays by distributing the configured delay time across content chunks.
- **FR-026**: The mock AI service MUST support streaming for both image-based and text-only conversations.

### Key Entities

- **SSE Chunk**: A single Server-Sent Event containing a `chat.completion.chunk` JSON object with incremental response data (delta). All chunks in one completion share the same ID and timestamp.
- **Stream Connection**: An active SSE connection between client and server. Has a lifecycle: opened, streaming, completed/terminated. Subject to timeout and concurrency limits.
- **Delta**: The incremental content object within an SSE chunk. Contains either a role assignment, a content token, or is empty (for stop/usage events). Replaces the `message` field used in non-streaming responses.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users see the first token of a streaming response within 200ms of sending their prompt.
- **SC-002**: The fully reassembled streaming response matches the non-streaming response content exactly (100% fidelity).
- **SC-003**: The system supports at least 10 concurrent streaming connections without response degradation or data mixing.
- **SC-004**: When a client disconnects mid-stream, the server stops processing within 1 second and releases all associated resources.
- **SC-005**: All SSE events pass validation against the OpenAI `chat.completion.chunk` schema (correct fields, types, and sequencing).
- **SC-006**: The non-streaming `/chat` endpoint continues to pass all existing tests after streaming is implemented (zero regressions).
- **SC-007**: Streaming requests exceeding the rate limit receive a 429 response before any SSE events are sent.
- **SC-008**: The client gracefully recovers from a failed stream by falling back to the non-streaming endpoint and displaying the complete response.

## Assumptions

- The streaming endpoint uses POST (not GET) to match the non-streaming chat endpoint's request format and to allow sending the prompt in the request body.
- Word-level tokenization (splitting on whitespace) is an acceptable approximation for mock streaming; production would use actual model tokenization.
- The 200ms first-token target refers to the time from request receipt to the first SSE event being sent, not including network latency.
- Streaming is applied to chat responses only; vision analysis responses (from `/upload`) remain non-streaming in this phase.
- The concurrent connection limit (default 50) applies globally, not per-session.
- Connection timeout (default 30 seconds) refers to the maximum duration of a single streaming response, not idle time between events.
