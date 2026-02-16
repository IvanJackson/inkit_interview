# Visual Assistant API - Phase 1 Complete ✅

A production-ready RESTful API for image upload and AI-powered conversational analysis. Built with Flask, featuring OpenAI-compatible responses, session management, and comprehensive validation.

## 🎯 Phase 1 Status: COMPLETE

**Implemented Features:**
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

The API will be available at `http://127.0.0.1:5000`

## 📖 API Usage

### 1. Upload Image (Basic)

```bash
curl -X POST http://127.0.0.1:5000/upload \
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

### 2. Upload Image with Prompt (Hybrid)

```bash
curl -X POST http://127.0.0.1:5000/upload \
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

### 3. Chat About Uploaded Image

```bash
curl -X POST http://127.0.0.1:5000/chat \
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

### 4. Handle Corrupted Images

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
curl -X POST http://127.0.0.1:5000/upload/confirm \
  -H "Content-Type: application/json" \
  -d '{"image_id": "uuid", "action": "confirm_valid"}'
```

## 🧪 Testing

### Run Unit Tests

```bash
# All tests
pytest tests/ -v

# Specific test suite
pytest tests/unit/test_openai_formatter.py -v
pytest tests/unit/test_security.py -v
```

### Run Example Scripts

```bash
# Test basic upload workflow
python test_scripts/test_upload_basic.py

# Test hybrid upload (image + prompt)
python test_scripts/test_upload_with_prompt.py

# Test chat workflow
python test_scripts/test_chat_workflow.py

# Verify OpenAI format compatibility
python test_scripts/test_openai_format.py
```

**Current Test Status:** ✅ 41/41 passing

## 📁 Project Structure

```
.
├── src/
│   ├── api/              # API endpoints
│   │   ├── upload.py     # /upload, /upload/confirm
│   │   ├── chat.py       # /chat, session management
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
│   │   └── mock_openai_service.py # Mock AI responses
│   └── utils/            # Utilities
│       ├── openai_formatter.py    # OpenAI format helpers
│       └── security.py            # Input validation, XSS/SQL prevention
├── tests/
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests (planned)
├── test_scripts/         # Example usage scripts
├── specs/                # Feature specifications
├── app.py                # Flask application entry point
├── config.py             # Configuration
└── requirements.txt      # Dependencies
```

## 🔒 Security Features

- **Input Validation**: File type, size (≤16MB), dimensions (≤4096x4096)
- **Content Validation**: Magic number verification, metadata extraction
- **XSS Prevention**: Pattern detection for `<script>`, `javascript:`, event handlers
- **SQL Injection Prevention**: Pattern detection for SQL keywords
- **Path Traversal Prevention**: `../` detection in filenames
- **Unicode Support**: Full Unicode with control character filtering
- **Rate Limiting**: 20 uploads/hour, 100 chats/minute per session
- **Secure Sessions**: Browser/device fingerprinting, re-auth on device switch

## 🎯 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/upload` | POST | Upload image (optionally with prompt) |
| `/upload/confirm` | POST | Confirm corrupted image handling |
| `/chat` | POST | Ask question about uploaded image |
| `/chat/relevance` | POST | Handle photo relevance switch |
| `/session/restore` | POST | Restore expired session |

## 📊 OpenAI API Compatibility

This implementation matches OpenAI API formats exactly:

**Vision Analysis** → **Responses API Format**
- Uses `output` array with message objects
- Content blocks with `type: "output_text"`
- Token usage: `input_tokens`, `output_tokens`

**Chat Completion** → **Chat Completions API Format**
- Uses `choices` array with message objects
- Token usage: `prompt_tokens`, `completion_tokens`
- Includes `finish_reason`, `logprobs`, `service_tier`

## 🚧 Roadmap

### Question 2: Streaming Responses (Planned)
- Server-Sent Events (SSE) for real-time responses
- Backpressure handling
- Reconnection logic

### Question 3: Conversation History (Planned)
- Multi-turn conversation storage
- Context-aware responses
- History cleanup

### Question 4: Production Database (Planned)
- SQLAlchemy + PostgreSQL
- Database migrations
- Caching layer

## 📝 Documentation

- [Quickstart Guide](specs/001-foundational-api/quickstart.md) - Detailed API usage examples
- [Feature Specification](specs/001-foundational-api/spec.md) - Complete requirements
- [Implementation Plan](specs/001-foundational-api/plan.md) - Architecture and design
- [Data Model](specs/001-foundational-api/data-model.md) - Entity definitions
- [Task Breakdown](specs/001-foundational-api/tasks.md) - Implementation tasks

## 🤝 Contributing

This is an interview project demonstrating production-ready API development. For questions or feedback, please open an issue.

## 📄 License

MIT License - See LICENSE file for details

---

**Built with:** Python 3.13, Flask, Pillow, Flask-Limiter, pytest
**OpenAI API Compatibility:** Responses API (vision), Chat Completions API (chat)
**Status:** Phase 1 Complete ✅ | All tests passing (41/41)
