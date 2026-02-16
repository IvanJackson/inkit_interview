# Visual Assistant API - Phase 2 Complete ✅

A production-ready RESTful API for image upload and AI-powered conversational analysis with real-time streaming responses. Built with Flask, featuring OpenAI-compatible SSE streaming, connection resilience, and comprehensive validation.

## 🎯 Implementation Status

### Phase 1: Foundational API ✅ COMPLETE
- ✅ Image upload with multi-layer validation (type, size, dimensions, content, metadata)
- ✅ Corrupted image detection with visual preview confirmation
- ✅ Session-based conversational chat (no explicit image IDs needed)
- ✅ Hybrid upload (optional prompt with image upload)
- ✅ OpenAI-compatible mock responses (Responses API for vision, Chat Completions for chat)
- ✅ Request queuing during upload processing
- ✅ Photo relevance analysis
- ✅ Session persistence and restoration
- ✅ Complete browser tab isolation
- ✅ Security: XSS/SQL injection prevention, Unicode support, rate limiting
- ✅ Concurrent request handling with thread safety

### Phase 2: Streaming Responses ✅ COMPLETE
- ✅ Server-Sent Events (SSE) streaming with OpenAI chat.completion.chunk format
- ✅ Word-by-word progressive rendering in browser
- ✅ Connection limit enforcement (50 concurrent streams via BoundedSemaphore)
- ✅ Stream timeout protection (30 second max per stream)
- ✅ Client disconnect detection (GeneratorExit handling)
- ✅ Automatic frontend fallback to non-streaming on failure
- ✅ Rate limiting on streaming endpoint (100 req/min)
- ✅ Concurrent stream isolation (no data mixing)
- ✅ Image analysis streaming support
- ✅ Comprehensive testing (73 unit tests + 12 integration tests)

## 🚀 Quick Start

### Prerequisites
- Python 3.13+ (or 3.8+)
- `pipenv` (recommended) or `venv`

### Installation

#### Option 1: Using pipenv (Recommended)

```bash
# Install dependencies
pipenv install

# Run the application
pipenv run python app.py
```

#### Option 2: Using venv

```bash
# Create virtual environment
python -m venv venv

# Activate (Unix/macOS)
source venv/bin/activate

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

The API will be available at `http://127.0.0.1:5001`

## 📖 API Usage

### 1. Chat with Streaming (Real-Time Response)

```bash
curl -N -X POST http://127.0.0.1:5001/chat/stream \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"prompt": "Tell me a story"}'
```

**Response (Server-Sent Events):**
```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"Once"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":" upon"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":" a"},"finish_reason":null}]}

...

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","choices":[{"index":0,"delta":{}}],"usage":{"prompt_tokens":10,"completion_tokens":50,"total_tokens":60}}

data: [DONE]
```

**Note:** Streaming responses appear word-by-word in real-time. Use the browser UI at `http://127.0.0.1:5001` for the best experience.

### 2. Upload Image (Basic)

```bash
curl -X POST http://127.0.0.1:5001/upload \
  -F "image=@photo.jpg" \
  -c cookies.txt
```

**Response:**
```json
{
  "image_id": "uuid",
  "filename": "photo.jpg",
  "size_bytes": 12345,
  "width": 1920,
  "height": 1080,
  "format": "JPEG",
  "uploaded_at": "2026-02-16T04:40:37.820334",
  "analysis": {
    "id": "resp_...",
    "object": "response",
    "output": [{
      "content": [{
        "type": "output_text",
        "text": "This appears to be a portrait with good focus..."
      }]
    }]
  }
}
```

### 3. Upload Image with Prompt (Hybrid)

```bash
curl -X POST http://127.0.0.1:5001/upload \
  -F "image=@photo.jpg" \
  -F "prompt=What colors do you see?" \
  -c cookies.txt
```

**Response includes both vision analysis AND chat response:**
```json
{
  "image_id": "uuid",
  "analysis": { ... },
  "chat_response": {
    "id": "chatcmpl-...",
    "object": "chat.completion",
    "choices": [{
      "message": {
        "role": "assistant",
        "content": "The image has warm tones and vibrant hues..."
      }
    }]
  }
}
```

### 4. Chat About Uploaded Image (Non-Streaming)

```bash
curl -X POST http://127.0.0.1:5001/chat \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"prompt": "What is the main subject?"}'
```

**Response:**
```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "The main subject is..."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "total_tokens": 150
  }
}
```

### 5. Stream Image Analysis

```bash
# Upload image first
IMAGE_ID=$(curl -s -X POST http://127.0.0.1:5001/upload \
  -F "image=@photo.jpg" \
  -c cookies.txt | jq -r '.image_id')

# Stream analysis of the uploaded image
curl -N -X POST http://127.0.0.1:5001/chat/stream \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d "{\"prompt\": \"Describe this image\", \"image_id\": \"$IMAGE_ID\"}"
```

**Note:** Image analysis also streams word-by-word, just like text-only chat.

### 6. Handle Corrupted Images

If corruption is detected, you'll receive:
```json
{
  "error": {
    "message": "Image appears corrupted. Please confirm if you want to proceed.",
    "code": "corruption_suspected"
  },
  "image_id": "uuid",
  "preview_base64": "data:image/jpeg;base64,...",
  "confirmation_url": "/upload/confirm"
}
```

Confirm or reject:
```bash
curl -X POST http://127.0.0.1:5001/upload/confirm \
  -H "Content-Type: application/json" \
  -d '{"image_id": "uuid", "action": "confirm_valid"}'
```

## 🧪 Testing

### Run Unit Tests

```bash
# All tests (73 total)
python3 -m pytest tests/ -v

# Specific test suites
pytest tests/unit/test_streaming.py -v      # 36 streaming tests
pytest tests/unit/test_openai_formatter.py -v
pytest tests/unit/test_security.py -v
```

**Current Test Status:** ✅ 73/73 passing

### Run Streaming Validation (End-to-End)

```bash
# Terminal 1: Start the server
python3 app.py

# Terminal 2: Run comprehensive validation
python3 validate_streaming.py

# Run specific test
python3 validate_streaming.py 7  # Test connection limits
```

**Validation Coverage:**
- ✅ SSE format compliance (FR-006 through FR-014)
- ✅ First token latency <200ms (SC-001)
- ✅ Content reassembly (SC-002)
- ✅ Client disconnect detection (FR-015)
- ✅ Stream timeout enforcement (FR-020, SC-004)
- ✅ Concurrent streams with no mixing (SC-003, FR-022)
- ✅ Connection limit (503 at 50 streams) (FR-018, FR-019)
- ✅ Rate limiting (429 after 100/min) (SC-007, FR-005)
- ✅ Error handling before streaming (FR-001, FR-003)
- ✅ Client-side fallback mechanism (FR-016, FR-017)
- ✅ Image streaming support (FR-022, FR-024, FR-026)
- ✅ Single response for upload+prompt

### Manual UI Testing

Open `http://127.0.0.1:5001` in your browser and follow [UI_TESTING_INSTRUCTIONS.md](UI_TESTING_INSTRUCTIONS.md) for interactive testing scenarios including:
- Normal streaming behavior
- Server disconnect mid-stream
- Network failure simulation
- Fallback to non-streaming
- Concurrent streams in multiple tabs

## 📁 Project Structure

```
.
├── src/
│   ├── api/              # API endpoints
│   │   ├── upload.py     # /upload, /upload/confirm
│   │   ├── chat.py       # /chat, /chat/stream (SSE), session management
│   │   └── middleware.py # Error handling, rate limiting
│   ├── models/           # Data models
│   │   ├── image.py      # Image entity
│   │   ├── session.py    # Session context
│   │   ├── chat.py       # Chat requests
│   │   └── response.py   # OpenAI response models
│   ├── services/         # Business logic
│   │   ├── image_service.py       # Upload, validation, corruption detection
│   │   ├── session_service.py     # Session tracking, persistence
│   │   ├── chat_service.py        # Chat processing, queuing
│   │   └── mock_openai_service.py # Mock AI responses with streaming
│   └── utils/            # Utilities
│       ├── openai_formatter.py    # SSE chunk formatting, OpenAI format helpers
│       └── security.py            # Input validation, XSS/SQL prevention
├── static/
│   └── index.html        # Browser UI with streaming + fallback
├── tests/
│   └── unit/             # Unit tests (73 total)
│       ├── test_streaming.py      # 36 streaming-specific tests
│       ├── test_openai_formatter.py
│       └── test_security.py
├── specs/                # Feature specifications
│   ├── 001-foundational-api/      # Phase 1 specs
│   └── 002-streaming-responses/   # Phase 2 specs
├── app.py                # Flask application entry point
├── config.py             # Configuration (includes streaming limits)
├── validate_streaming.py # End-to-end streaming validation (12 tests)
├── UI_TESTING_INSTRUCTIONS.md    # Manual UI testing guide
├── Q2_IMPLEMENTATION_SUMMARY.md  # Phase 2 technical summary
└── requirements.txt      # Dependencies
```

## 🔒 Security & Protection

### Input Validation
- **File type, size (≤16MB), dimensions (≤4096x4096)**
- **Content Validation**: Magic number verification, metadata extraction
- **XSS Prevention**: Pattern detection for `<script>`, `javascript:`, event handlers
- **SQL Injection Prevention**: Pattern detection for SQL keywords
- **Path Traversal Prevention**: `../` detection in filenames
- **Unicode Support**: Full Unicode with control character filtering

### Rate Limiting & Backpressure
- **Upload Rate**: 20 uploads/hour per session
- **Chat Rate**: 100 requests/minute per session (applies to both `/chat` and `/chat/stream`)
- **Connection Limit**: Max 50 concurrent streaming connections (BoundedSemaphore)
- **Stream Timeout**: 30 second maximum per stream
- **Error Responses**: 429 (rate limit), 503 (capacity exceeded)

### Session Security
- **Browser/device fingerprinting**: Prevents session hijacking
- **Re-authentication**: Required on device switch
- **Session timeout**: 24 hours of inactivity

## 🎯 API Endpoints

| Endpoint | Method | Description | Response Format |
|----------|--------|-------------|-----------------|
| `/` | GET | Browser UI with streaming support | HTML |
| `/upload` | POST | Upload image (optionally with prompt) | JSON |
| `/upload/confirm` | POST | Confirm corrupted image handling | JSON |
| `/chat` | POST | Ask question (non-streaming) | JSON |
| **`/chat/stream`** | **POST** | **Ask question (streaming SSE)** | **text/event-stream** |
| `/chat/relevance` | POST | Handle photo relevance switch | JSON |
| `/session/restore` | POST | Restore expired session | JSON |

### Streaming Endpoint Details

**`POST /chat/stream`** returns Server-Sent Events (SSE) with OpenAI chat.completion.chunk format:

- **Content-Type**: `text/event-stream`
- **Chunk Format**: `data: {json}\n\n`
- **Sequence**: role → content (N chunks) → stop → usage → [DONE]
- **Error Codes**: 400 (invalid prompt), 429 (rate limit), 503 (capacity exceeded)
- **Timeout**: Automatically terminates after 30 seconds
- **Fallback**: Frontend automatically retries via `/chat` on failure

## 📊 OpenAI API Compatibility

This implementation matches OpenAI API formats exactly:

**Vision Analysis** → **Responses API Format**
- Uses `output` array with message objects
- Content blocks with `type: "output_text"`
- Token usage: `input_tokens`, `output_tokens`

**Chat Completion (Non-Streaming)** → **Chat Completions API Format**
- Uses `choices` array with message objects
- Token usage: `prompt_tokens`, `completion_tokens`
- Includes `finish_reason`, `logprobs`, `service_tier`

**Chat Completion (Streaming)** → **Chat Completions Streaming API Format**
- Server-Sent Events (SSE) with `text/event-stream` Content-Type
- Each chunk: `object: "chat.completion.chunk"`
- Uses `delta` (not `message`) in choices
- Chunk sequence: role → content chunks → stop (finish_reason) → usage → [DONE]
- All chunks share same `id` for reassembly
- Matches OpenAI streaming behavior exactly

## 🚧 Roadmap

### ✅ Phase 1: Foundational API (COMPLETE)
- Image upload with validation
- Session-based chat
- OpenAI-compatible responses
- Security & rate limiting

### ✅ Phase 2: Streaming Responses (COMPLETE)
- Server-Sent Events (SSE) for real-time responses
- Backpressure handling (connection limits, timeouts)
- Frontend fallback mechanism
- Comprehensive testing

### 🚧 Phase 3: Conversation History (Planned)
- Multi-turn conversation storage
- Context-aware responses
- History cleanup

### 🚧 Phase 4: Production Database (Planned)
- SQLAlchemy + PostgreSQL
- Database migrations
- Caching layer

## 📝 Documentation

### Phase 1: Foundational API
- [Quickstart Guide](specs/001-foundational-api/quickstart.md) - Detailed API usage examples
- [Feature Specification](specs/001-foundational-api/spec.md) - Complete requirements
- [Implementation Plan](specs/001-foundational-api/plan.md) - Architecture and design
- [Data Model](specs/001-foundational-api/data-model.md) - Entity definitions
- [Task Breakdown](specs/001-foundational-api/tasks.md) - Implementation tasks

### Phase 2: Streaming Responses
- [Q2 Implementation Summary](Q2_IMPLEMENTATION_SUMMARY.md) - **Start here** - comprehensive technical overview
- [Feature Specification](specs/002-streaming-responses/spec.md) - Requirements and user stories
- [Implementation Plan](specs/002-streaming-responses/plan.md) - Architecture decisions
- [Task Breakdown](specs/002-streaming-responses/tasks.md) - All 32 tasks with dependencies
- [UI Testing Guide](UI_TESTING_INSTRUCTIONS.md) - Manual browser testing scenarios
- [Validation Script](validate_streaming.py) - 12 end-to-end tests with visible proof

## 🤝 Contributing

This is an interview project demonstrating production-ready API development. For questions or feedback, please open an issue.

## 📄 License

MIT License - See LICENSE file for details

---

**Built with:** Python 3.13, Flask, Pillow, Flask-Limiter, pytest
**OpenAI API Compatibility:** Responses API (vision), Chat Completions API (chat + streaming)
**Status:** Phase 2 Complete ✅ | All tests passing (73/73 unit tests + 12/12 validation tests)
**Streaming:** SSE with word-by-word rendering, 50 concurrent streams, 30s timeout, automatic fallback
