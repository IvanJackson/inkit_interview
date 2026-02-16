# Research: Foundational API - Image Upload and Basic Chat

**Feature**: 001-foundational-api
**Date**: 2026-02-14
**Purpose**: Resolve technical unknowns and establish implementation patterns for Phase 1 design

## Research Areas

### 1. OpenAI API Response Format Specifications

**Decision**: Implement exact OpenAI Chat Completion and Vision API response formats

**Rationale**:
- Constitution Principle II (NON-NEGOTIABLE): Responses must match OpenAI API exactly
- Enables drop-in compatibility with OpenAI client libraries
- Simplifies future migration from mock to real OpenAI services

**OpenAI Chat Completion Format** (non-streaming):
```json
{
  "id": "chatcmpl-{unique_id}",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-4-vision-preview",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "The response text here"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 56,
    "completion_tokens": 31,
    "total_tokens": 87
  }
}
```

**OpenAI Vision Analysis Format**:
```json
{
  "id": "chatcmpl-{unique_id}",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-4-vision-preview",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "This image shows..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 45,
    "total_tokens": 145
  }
}
```

**Implementation Pattern**:
- Create `utils/openai_formatter.py` with helper functions
- All mock responses use same format builder
- Include all required fields: id (chatcmpl- prefix), object, created (Unix timestamp), model, choices array, usage stats
- finish_reason values: "stop", "length", "content_filter", "null"

**Alternatives Considered**:
- Custom response format: Rejected - breaks OpenAI compatibility requirement
- Partial OpenAI format: Rejected - could cause subtle incompatibilities

**References**: OpenAI API documentation (chat completions endpoint spec)

---

### 2. Image Validation and Corruption Detection

**Decision**: Use Pillow (PIL) for multi-layer image validation with corruption detection

**Rationale**:
- Industry-standard Python library for image processing
- Can validate file content beyond extensions (FR-005)
- Extracts metadata (dimensions, format, color space) - FR-006
- Detects corruption during image opening - FR-007
- Generates preview images for confirmation - FR-008

**Validation Layers**:
1. **Extension check**: Quick pre-filter (JPEG, PNG, GIF, WebP)
2. **Magic number verification**: Read file header to confirm actual type
3. **Pillow Image.open()**: Validates file can be decoded
4. **Metadata extraction**: Get dimensions, format, mode (RGB/RGBA/etc.)
5. **Dimension validation**: Enforce 4096x4096 maximum
6. **Corruption detection**: If Image.open() raises exceptions or image verify() fails

**Corruption Handling Pattern**:
```python
from PIL import Image
try:
    with Image.open(file_path) as img:
        img.verify()  # Detect corruption
        # Re-open for metadata (verify closes file)
        img = Image.open(file_path)
        width, height = img.size
        format = img.format
        mode = img.mode
        # If suspicious, generate thumbnail preview for user
        if needs_confirmation:
            preview = img.copy()
            preview.thumbnail((200, 200))
            return preview_as_base64
except (IOError, SyntaxError, Image.DecompressionBombError) as e:
    # Handle corruption - render preview if possible, or reject
    handle_corrupted_image(e)
```

**Metadata Extraction Failure**:
- If metadata extraction fails (FR-006): Reject with clear error
- Error message: "Unsupported image format or file may be corrupted"
- HTTP Status: 422 Unprocessable Entity

**Alternatives Considered**:
- ImageMagick: Rejected - adds external dependency, overkill for Phase 1
- File command-line tool: Rejected - less portable, harder to extract metadata
- imghdr module: Rejected - doesn't provide dimension/metadata extraction

**References**: Pillow documentation, Python image processing best practices

---

### 3. Session Management and Persistence

**Decision**: In-memory session store with thread-safe dictionary + locks for Phase 1

**Rationale**:
- Constitution allows in-memory storage for rapid Phase 1 iteration
- Thread-safe required for Flask threaded mode (FR-033)
- Session persistence across expiry/reconnection (FR-034, FR-035)
- Browser tab isolation (FR-033)

**Session Storage Pattern**:
```python
import threading
from typing import Dict
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class SessionContext:
    session_id: str
    current_image_id: str | None
    conversation_topic: str | None
    browser_device_id: str
    created_at: datetime
    last_activity: datetime
    authenticated: bool

class SessionService:
    def __init__(self):
        self._sessions: Dict[str, SessionContext] = {}
        self._lock = threading.RLock()
        self._session_timeout = timedelta(hours=24)

    def get_session(self, session_id: str) -> SessionContext | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session and self._is_expired(session):
                # Persist for later restoration
                self._persist_expired_session(session)
                del self._sessions[session_id]
                return None
            return session

    def update_session(self, session: SessionContext):
        with self._lock:
            session.last_activity = datetime.now()
            self._sessions[session.session_id] = session
```

**Session Identification**:
- Cookie-based session ID (Flask session management)
- Browser/device fingerprinting for tab isolation
- Re-authentication required on device switch (FR-037)

**Persistence Strategy**:
- In-memory for active sessions (< 100 assumed for Phase 1)
- Expired sessions serialized to dict for potential restoration
- Will migrate to Redis/database in Question 4

**Alternatives Considered**:
- Flask-Session extension: Considered but adds complexity for Phase 1 in-memory needs
- Redis immediately: Rejected - constitution encourages in-memory for Phase 1
- No persistence: Rejected - violates FR-034, FR-035

**References**: Flask session management, Python threading best practices

---

### 4. Request Queuing During Upload

**Decision**: In-memory queue per image with upload completion callback

**Rationale**:
- Silly excuse responses < 500ms (SC-007)
- Automatic processing after upload (FR-024, SC-008)
- Thread-safe queue management

**Queuing Pattern**:
```python
from queue import Queue
from dataclasses import dataclass

@dataclass
class QueuedRequest:
    chat_request: ChatRequest
    queued_at: datetime
    session_id: str

class UploadQueueService:
    def __init__(self):
        self._queues: Dict[str, Queue[QueuedRequest]] = {}
        self._upload_status: Dict[str, str] = {}  # image_id -> status
        self._lock = threading.RLock()

    def is_upload_in_progress(self, image_id: str) -> bool:
        with self._lock:
            return self._upload_status.get(image_id) == "uploading"

    def queue_request(self, image_id: str, request: QueuedRequest):
        with self._lock:
            if image_id not in self._queues:
                self._queues[image_id] = Queue()
            self._queues[image_id].put(request)

    def on_upload_complete(self, image_id: str):
        with self._lock:
            self._upload_status[image_id] = "complete"
            # Process all queued requests
            if image_id in self._queues:
                while not self._queues[image_id].empty():
                    queued = self._queues[image_id].get()
                    self._process_queued_request(queued)
```

**Silly Excuse Generation**:
- Random selection from pre-defined list
- Examples: "I went to the bathroom", "I'm fetching the dog", "I'm making coffee", "I stepped out for fresh air", "I'm watering the plants"
- Formatted as OpenAI chat completion (FR-049)
- Response time < 500ms (immediate, no AI call needed)

**Alternatives Considered**:
- Celery/task queue: Rejected - too complex for Phase 1, external dependency
- Polling: Rejected - inefficient, worse UX than callback pattern
- Block requests: Rejected - violates FR-023, FR-024 requirements

---

### 5. Photo Relevance Analysis

**Decision**: Mock analysis with keyword/topic matching for Phase 1

**Rationale**:
- 90%+ accuracy requirement (SC-009) achievable with simple heuristics in mock
- Phase 1 uses mock services (no real AI)
- Pattern ready for real AI integration in future

**Mock Relevance Pattern**:
```python
def analyze_photo_relevance(
    current_topic: str,
    new_image_id: str
) -> bool:
    """
    Mock photo relevance analysis.
    Returns True if new image likely related to current conversation.
    """
    # For Phase 1 mock: simple heuristics
    # - If no current topic, always related (first image)
    # - Extract basic features from new image (color dominance, aspect ratio)
    # - Compare with conversation topic keywords

    if not current_topic:
        return True

    # Mock logic: use image filename, size, aspect ratio as proxy
    # Real implementation in future: actual vision model similarity
    new_features = extract_mock_features(new_image_id)
    similarity_score = calculate_mock_similarity(current_topic, new_features)

    # Threshold: < 0.3 similarity = unrelated
    return similarity_score >= 0.3
```

**Conversation Switch Prompt** (FR-029):
- Format: "This looks like a different topic - would you like to start a new conversation?"
- Formatted as OpenAI chat completion (FR-050)
- Wait for user confirmation before switching context (FR-030)

**Alternatives Considered**:
- Always prompt on new image: Rejected - annoying UX if uploading similar images
- Never prompt: Rejected - violates FR-028, FR-029, FR-030
- Real AI analysis in Phase 1: Rejected - out of scope, mock services only

**Future Enhancement**: Replace with actual vision model similarity in production

---

### 6. Rate Limiting Implementation

**Decision**: Flask-Limiter with in-memory storage backend

**Rationale**:
- Industry standard for Flask applications
- Supports multiple limit strategies (per-route, per-session, per-IP)
- Clean decorator-based API
- In-memory sufficient for Phase 1

**Rate Limiting Configuration**:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,  # Default to IP-based
    default_limits=["1000 per hour"],  # Global limit
    storage_uri="memory://"  # In-memory for Phase 1
)

@app.route('/upload', methods=['POST'])
@limiter.limit("20 per hour", key_func=lambda: get_session_id())
def upload_image():
    # Upload logic

@app.route('/chat', methods=['POST'])
@limiter.limit("100 per minute", key_func=lambda: get_session_id())
def chat():
    # Chat logic
```

**Limits**:
- Upload: 20 requests/hour per session
- Chat: 100 requests/minute per session
- Global: 1000 requests/hour per IP
- Response: 429 Too Many Requests with Retry-After header

**Alternatives Considered**:
- Redis-backed limiter: Deferred to Question 4 (database persistence phase)
- Custom rate limiting: Rejected - reinventing wheel, Flask-Limiter battle-tested
- No rate limiting: Rejected - violates security principles

**References**: Flask-Limiter documentation, REST API rate limiting best practices

---

### 7. Thread Safety for Concurrent Access

**Decision**: Python threading.RLock for all shared state + Flask threaded mode

**Rationale**:
- Flask runs in threaded mode (app.run(threaded=True))
- Shared dictionaries (images, sessions, queues) need protection
- RLock allows re-entrant locking (same thread can acquire multiple times)
- Zero race conditions required (SC-014)

**Thread-Safety Pattern**:
```python
import threading

class ImageService:
    def __init__(self):
        self._images: Dict[str, Image] = {}
        self._lock = threading.RLock()

    def add_image(self, image: Image):
        with self._lock:
            self._images[image.id] = image

    def get_image(self, image_id: str) -> Image | None:
        with self._lock:
            return self._images.get(image_id)
```

**Concurrent Testing Strategy**:
- Use Python threading module to spawn concurrent requests
- Pytest with pytest-xdist for parallel test execution
- Test scenarios: 10+ concurrent uploads (SC-002), 10+ concurrent chats (SC-004)
- Verify: no data corruption, no response mixing, correct session isolation

**Alternatives Considered**:
- Asyncio: Rejected - Flask sync model simpler for Phase 1
- Process-based concurrency: Rejected - overkill, adds complexity
- No locking: Rejected - guaranteed race conditions

**References**: Python threading documentation, Flask concurrency patterns

---

### 8. Error Response Patterns

**Decision**: Consistent error response format matching OpenAI error structure

**Rationale**:
- Maintain OpenAI compatibility for errors
- Clear, actionable messages (FR-015, FR-040)
- Never expose internal details

**Error Response Format**:
```json
{
  "error": {
    "message": "Image file exceeds maximum size of 16MB",
    "type": "invalid_request_error",
    "param": "image",
    "code": "image_too_large"
  }
}
```

**Error Type Mapping**:
- 400 Bad Request: `invalid_request_error`
- 404 Not Found: `invalid_request_error` with specific message
- 413 Payload Too Large: `invalid_request_error` (image_too_large)
- 415 Unsupported Media Type: `invalid_request_error` (unsupported_format)
- 422 Unprocessable Entity: `invalid_request_error` (validation_failed)
- 423 Locked (upload in progress): `invalid_request_error` (resource_busy)
- 429 Too Many Requests: `rate_limit_exceeded`
- 500 Internal Server Error: `api_error`

**Error Messages**:
- Always actionable: Tell user what to fix
- Never expose: Stack traces, file paths, internal IDs
- Include: What failed, why it failed, how to fix

**Alternatives Considered**:
- Plain text errors: Rejected - harder to parse, less professional
- Custom error format: Rejected - breaks OpenAI compatibility
- Verbose error details: Rejected - security risk

---

## Summary

All technical unknowns resolved with clear implementation patterns:

1. **OpenAI Formats**: Exact chat completion & vision response structures defined
2. **Image Validation**: Pillow-based multi-layer validation with corruption detection
3. **Session Management**: Thread-safe in-memory store with persistence hooks
4. **Request Queuing**: In-memory queue with upload completion callbacks
5. **Photo Relevance**: Mock heuristic analysis (ready for real AI later)
6. **Rate Limiting**: Flask-Limiter with in-memory backend
7. **Thread Safety**: RLock-based protection for all shared state
8. **Error Responses**: OpenAI-compatible error format

**Ready for Phase 1**: Design (data model, API contracts, quickstart)
