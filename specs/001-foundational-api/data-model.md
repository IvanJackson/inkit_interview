# Data Model: Foundational API - Image Upload and Basic Chat

**Feature**: 001-foundational-api
**Date**: 2026-02-14
**Storage**: In-memory dictionaries (Phase 1) → Database migration (Question 4)

## Overview

This document defines the core data entities for the foundational Visual Assistant API. All entities are stored in-memory using Python dictionaries with thread-safe access patterns (RLock). Entity relationships are maintained through ID references.

## Entities

### 1. Image

Represents an uploaded image file with validation state and metadata.

**Fields**:
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `id` | `str` (UUID) | Yes | Unique identifier for the image | Generated on creation |
| `filename` | `str` | Yes | Original filename from upload | Sanitized, max 255 chars |
| `size_bytes` | `int` | Yes | File size in bytes | ≤ 16MB (16,777,216 bytes) |
| `width` | `int` | Yes | Image width in pixels | ≤ 4096 |
| `height` | `int` | Yes | Image height in pixels | ≤ 4096 |
| `format` | `str` | Yes | Image format (JPEG, PNG, GIF, WebP) | Validated against allowed types |
| `mode` | `str` | Yes | Color mode (RGB, RGBA, etc.) | From Pillow metadata |
| `file_path` | `str` | Yes | Storage path on filesystem | Secure path in uploads/ directory |
| `uploaded_at` | `datetime` | Yes | Upload timestamp | UTC timezone |
| `corruption_status` | `str` | Yes | Validation state: "valid", "suspected", "confirmed" | Enum-like validation |
| `preview_data` | `str \| None` | No | Base64-encoded preview for corrupted images | Generated if corruption suspected |
| `vision_analysis` | `str \| None` | No | Initial AI vision analysis result | Generated on successful upload |

**Relationships**:
- Referenced by: `SessionContext.current_image_id`
- Referenced by: `ChatRequest.image_id`
- Referenced by: `QueuedRequest` (via upload_image_id)

**State Transitions**:
```
[Upload] → corruption_status="valid" → [Available for chat]
         ↓
         corruption_status="suspected" → [Preview to user]
                          ↓
         [User confirms] → corruption_status="confirmed" → [Rejected]
```

**Storage Pattern** (Phase 1):
```python
image_store: Dict[str, Image] = {}  # Key: image.id, Value: Image
image_store_lock = threading.RLock()
```

---

### 2. SessionContext

Represents a user's interaction session with persistence across disconnections.

**Fields**:
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `session_id` | `str` (UUID) | Yes | Unique session identifier | From Flask session or cookie |
| `current_image_id` | `str \| None` | No | ID of most recently uploaded image | Must exist in image_store |
| `conversation_topic` | `str \| None` | No | Current conversation topic summary | Max 500 chars |
| `browser_device_id` | `str` | Yes | Browser/device fingerprint for isolation | Hash of User-Agent + other headers |
| `created_at` | `datetime` | Yes | Session creation timestamp | UTC timezone |
| `last_activity` | `datetime` | Yes | Last request timestamp | UTC timezone, updated on each request |
| `authenticated` | `bool` | Yes | Authentication status | Required for device switching |
| `expired` | `bool` | No | Whether session has expired | True if last_activity > 24 hours |

**Relationships**:
- References: `Image` via `current_image_id`
- Referenced by: `ChatRequest.session_id`
- Referenced by: `QueuedRequest.session_id`

**Business Rules**:
- Session timeout: 24 hours of inactivity
- Browser tab isolation: Separate session per `browser_device_id`
- Device switch: Requires re-authentication (`authenticated = False`)
- Persistence: Expired sessions serialized for potential restoration

**Storage Pattern** (Phase 1):
```python
session_store: Dict[str, SessionContext] = {}  # Key: session_id, Value: SessionContext
session_store_lock = threading.RLock()
expired_sessions: Dict[str, SessionContext] = {}  # For restoration
```

---

### 3. ChatRequest

Represents a user's question about an image (independent requests, no history in Phase 1).

**Fields**:
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `id` | `str` (UUID) | Yes | Unique request identifier | Generated on creation |
| `session_id` | `str` | Yes | Session making the request | Must exist in session_store |
| `image_id` | `str \| None` | No | Explicit image ID override | If None, use session.current_image_id |
| `prompt` | `str` | Yes | User's text question/prompt | 1-10,000 characters, sanitized |
| `created_at` | `datetime` | Yes | Request timestamp | UTC timezone |
| `queue_status` | `str` | Yes | "immediate" or "queued" | Set if upload in progress |

**Relationships**:
- References: `SessionContext` via `session_id`
- References: `Image` via `image_id` (explicit) or `SessionContext.current_image_id` (implicit)

**Validation Rules**:
- If `image_id` is None → use `session.current_image_id`
- If both None → Error 400 "Please upload an image first"
- If upload in progress → queue_status = "queued", create QueuedRequest
- prompt sanitized against XSS/injection

**Storage Pattern** (Phase 1):
```python
# Transient - not stored long-term in Phase 1 (no history)
# Only exists during request processing
```

---

### 4. QueuedRequest

Represents a chat request queued during image upload, automatically processed on completion.

**Fields**:
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `id` | `str` (UUID) | Yes | Unique queued request identifier | Generated on creation |
| `chat_request` | `ChatRequest` | Yes | The original chat request | Full ChatRequest object |
| `upload_image_id` | `str` | Yes | ID of image being uploaded | Must be in-progress |
| `queued_at` | `datetime` | Yes | Queueing timestamp | UTC timezone |
| `session_id` | `str` | Yes | Session that made request | For context restoration |

**Relationships**:
- Contains: `ChatRequest` (composition)
- References: `Image` via `upload_image_id` (in-progress upload)
- References: `SessionContext` via `session_id`

**Lifecycle**:
1. Created when chat arrives during upload
2. Stored in queue keyed by `upload_image_id`
3. Processed automatically when upload completes (< 1 second per SC-008)
4. Deleted after successful processing

**Storage Pattern** (Phase 1):
```python
queued_requests: Dict[str, List[QueuedRequest]] = {}  # Key: upload_image_id, Value: Queue
queue_lock = threading.RLock()
upload_status: Dict[str, str] = {}  # Key: image_id, Value: "uploading" | "complete"
```

---

### 5. Response

Represents AI service responses in OpenAI-compatible format.

**Fields**:
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `id` | `str` | Yes | Response ID with "chatcmpl-" prefix | Format: "chatcmpl-{UUID}" |
| `object` | `str` | Yes | Always "chat.completion" | Fixed value for OpenAI compatibility |
| `created` | `int` | Yes | Unix timestamp | UTC timezone, seconds since epoch |
| `model` | `str` | Yes | Model name identifier | Fixed: "gpt-4-vision-preview" for Phase 1 |
| `choices` | `List[Choice]` | Yes | Array of response choices | Length 1 for Phase 1 |
| `usage` | `Usage` | Yes | Token usage statistics | Mock values for Phase 1 |

**Nested Structures**:

**Choice**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `index` | `int` | Yes | Choice index (always 0 for Phase 1) |
| `message` | `Message` | Yes | The response message |
| `finish_reason` | `str` | Yes | "stop", "length", "content_filter", or null |

**Message**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `role` | `str` | Yes | Always "assistant" |
| `content` | `str` | Yes | The actual response text |

**Usage**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt_tokens` | `int` | Yes | Mock token count for prompt |
| `completion_tokens` | `int` | Yes | Mock token count for completion |
| `total_tokens` | `int` | Yes | Sum of prompt + completion |

**Response Types**:
1. **Vision Analysis** (after upload): Analysis of uploaded image
2. **Chat Response**: Answer to user question
3. **Silly Excuse**: During upload, explains why AI can't respond yet
4. **Photo Relevance Prompt**: "This looks like a different topic - would you like to start a new conversation?"

**Storage Pattern** (Phase 1):
```python
# Transient - returned immediately, not stored
# Future: Store in conversation history (Question 3)
```

---

## Entity Relationship Diagram

```
┌─────────────────┐
│  SessionContext │
│  - session_id   │
│  - current_image_id ────┐
│  - browser_device_id    │
│  - last_activity        │
└────────┬────────┘        │
         │                 │
         │ references      │
         ↓                 ↓
┌─────────────────┐   ┌──────────┐
│   ChatRequest   │   │  Image   │
│  - id           │   │  - id    │
│  - session_id   │   │  - filename │
│  - image_id ────────→  - size_bytes │
│  - prompt       │   │  - width │
│  - queue_status │   │  - height │
└────────┬────────┘   │  - format │
         │            │  - corruption_status │
         │            └──────────┘
         │                 ↑
         ↓                 │
┌──────────────────┐       │
│  QueuedRequest   │       │
│  - id            │       │
│  - chat_request  │       │
│  - upload_image_id ──────┘
│  - queued_at     │
└──────────────────┘

All entities generate Response objects (not stored in Phase 1)
```

## Storage Migration Path

**Phase 1 (Current)**: In-memory dictionaries with RLock
- Fast, simple, perfect for development
- Sessions persist across expiry (in-memory serialization)
- Limitations: Data lost on server restart, not scalable

**Question 4 (Future)**: SQLAlchemy + Persistent Database
- Entities map to database tables
- Relationships become foreign keys
- Session store moves to Redis for performance
- Image metadata in database, files on disk/S3

**Migration Strategy**:
- Entity structures already designed for database compatibility
- Add SQLAlchemy models mirroring these dataclasses
- Service layer abstracts storage (no API changes needed)
- Backward compatible: non-streaming endpoints remain unchanged

---

## Validation Summary

| Entity | Primary Validations |
|--------|---------------------|
| **Image** | Type (JPEG/PNG/GIF/WebP), Size (≤16MB), Dimensions (≤4096x4096), Content (Pillow validation), Metadata extraction |
| **SessionContext** | Session timeout (24h), Browser isolation (unique device IDs), Authentication on device switch |
| **ChatRequest** | Prompt length (1-10,000 chars), XSS/injection sanitization, Image reference exists, Unicode support |
| **QueuedRequest** | Upload in-progress check, Automatic processing on completion (< 1 sec) |
| **Response** | OpenAI format compliance, All required fields present, Consistent structure |

All validations enforced in service layer before entity creation.
