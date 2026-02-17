# Data Model: Conversation History

**Feature**: 003-conversation-history
**Date**: 2026-02-16

## Entity Definitions

### Conversation

Represents a multi-turn dialogue between a user and the assistant, optionally associated with an image.

| Field           | Type              | Constraints                  | Description                                    |
|-----------------|-------------------|------------------------------|------------------------------------------------|
| conversation_id | UUID (str)        | Primary key, auto-generated  | Unique identifier for the conversation         |
| image_id        | UUID (str)        | Nullable, references Image   | Image being discussed (None for text-only)     |
| session_id      | UUID (str)        | Required, references Session | Session that owns this conversation            |
| created_at      | datetime (UTC)    | Auto-set on creation         | When the conversation was started              |
| last_activity   | datetime (UTC)    | Updated on each new message  | Most recent message timestamp                  |

**Dataclass Definition**:
```python
@dataclass
class Conversation:
    conversation_id: str          # UUID
    session_id: str               # UUID - references SessionContext.session_id
    image_id: Optional[str]       # UUID - references uploaded image, or None
    created_at: datetime           # UTC timestamp
    last_activity: datetime        # UTC timestamp, updated on each message

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.last_activity is None:
            self.last_activity = datetime.utcnow()

    def touch(self):
        """Update last_activity to now."""
        self.last_activity = datetime.utcnow()
```

**Relationships**:
- **Contains**: One-to-many relationship with `Message` (a conversation has zero or more messages).
- **References**: `Image` via `image_id` (optional; text-only conversations have `image_id=None`).
- **References**: `SessionContext` via `session_id` (every conversation belongs to a session).

---

### Message

Represents a single message within a conversation, from either the user or the assistant.

| Field           | Type              | Constraints                        | Description                                    |
|-----------------|-------------------|------------------------------------|------------------------------------------------|
| message_id      | UUID (str)        | Primary key, auto-generated        | Unique identifier for the message              |
| conversation_id | UUID (str)        | Required, references Conversation  | Parent conversation                            |
| role            | str (enum)        | One of: "user", "assistant"        | Who sent the message                           |
| content         | str               | Max 50,000 characters              | Message text content                           |
| created_at      | datetime (UTC)    | Auto-set on creation               | When the message was sent                      |
| token_count     | int               | Computed, >= 0                     | Estimated token count (word_count * 2)         |

**Dataclass Definition**:
```python
@dataclass
class Message:
    message_id: str               # UUID
    conversation_id: str          # UUID - references Conversation.conversation_id
    role: str                     # "user" or "assistant"
    content: str                  # Message text, max 50,000 characters
    created_at: datetime           # UTC timestamp
    token_count: int              # Estimated as len(content.split()) * 2

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.token_count is None:
            self.token_count = len(self.content.split()) * 2

        # Validate role
        valid_roles = {"user", "assistant"}
        if self.role not in valid_roles:
            raise ValueError(f"Invalid role: {self.role}. Must be one of {valid_roles}")

        # Validate content length
        if len(self.content) > 50_000:
            raise ValueError(f"Content exceeds maximum length of 50,000 characters")
```

**Relationships**:
- **Belongs to**: `Conversation` via `conversation_id`.

---

### HistoryRetentionPolicy (Configuration Only)

Not a stored entity. Defined as configuration values in `config.py`.

| Setting             | Type  | Default | Description                                         |
|---------------------|-------|---------|-----------------------------------------------------|
| retention_days      | int   | 30      | Days after last_activity before marking for cleanup  |
| grace_period_days   | int   | 7       | Additional days before permanent deletion            |

**Config Integration**:
```python
# In config.py (Config class)
HISTORY_RETENTION_DAYS = 30
HISTORY_GRACE_PERIOD_DAYS = 7
HISTORY_CLEANUP_INTERVAL_SECONDS = 3600  # 1 hour
HISTORY_MAX_MESSAGES = 50
HISTORY_MAX_TOKENS = 10_000
```

---

## Storage Indexes

All indexes are maintained as in-memory dictionaries, protected by the service's `threading.RLock`.

| Index Name                 | Key Type         | Value Type          | Purpose                                      |
|----------------------------|------------------|---------------------|----------------------------------------------|
| `_conversations`           | conversation_id  | Conversation        | Primary lookup by conversation ID            |
| `_messages`                | conversation_id  | List[Message]       | All messages for a conversation (ordered)    |
| `_conversations_by_image`  | image_id         | List[str]           | Find conversations about a specific image    |
| `_conversations_by_session`| session_id       | List[str]           | Find all conversations in a session          |

**Index Maintenance**:
- When a `Conversation` is created, its `conversation_id` is appended to both `_conversations_by_image[image_id]` and `_conversations_by_session[session_id]`.
- When a `Conversation` is deleted (cleanup), its ID is removed from all three indexes and its messages are removed from `_messages`.
- All index operations occur within the same `RLock` acquisition as the primary operation to maintain consistency.

---

## Entity Relationship Diagram

```
+------------------+       +------------------+       +------------------+
|  SessionContext   |       |   Conversation    |       |     Message       |
|  (existing)      |       |   (new)           |       |     (new)         |
+------------------+       +------------------+       +------------------+
| session_id  [PK] |<------| session_id  [FK] |       | message_id  [PK] |
| current_image_id |       | conversation_id   |<------| conversation_id  |
| browser_device_id|       |   [PK]           |       |   [FK]           |
| created_at       |       | image_id    [FK] |       | role             |
| last_activity    |       | created_at       |       | content          |
| authenticated    |       | last_activity    |       | created_at       |
| expired          |       +------------------+       | token_count      |
+------------------+              |                    +------------------+
                                  |
                                  v
                          +------------------+
                          |   Image           |
                          |   (existing)      |
                          +------------------+
                          | image_id    [PK] |
                          | filename         |
                          | upload_status    |
                          | ...              |
                          +------------------+

Relationships:
  SessionContext  1 --- * Conversation   (a session has many conversations)
  Conversation    1 --- * Message         (a conversation has many messages)
  Image           1 --- * Conversation   (an image can be discussed in many conversations)
```

---

## Data Flow Examples

### Flow 1: First Message in a New Conversation

```
User sends: POST /chat { "prompt": "What do you see?", "image_id": "abc-123" }

1. Resolve session (existing pattern)
2. Check if active conversation exists for (session_id, image_id)
   - No active conversation found
3. Create new Conversation:
   {
     conversation_id: "conv-001",
     session_id: "sess-xyz",
     image_id: "abc-123",
     created_at: "2026-02-16T10:00:00Z",
     last_activity: "2026-02-16T10:00:00Z"
   }
4. Update indexes:
   _conversations["conv-001"] = conversation
   _conversations_by_image["abc-123"].append("conv-001")
   _conversations_by_session["sess-xyz"].append("conv-001")
5. Record user Message:
   {
     message_id: "msg-001",
     conversation_id: "conv-001",
     role: "user",
     content: "What do you see?",
     token_count: 8
   }
6. Retrieve truncated history (just this one message) for context injection
7. Call mock_openai_chat() with history-augmented prompt
8. Record assistant Message:
   {
     message_id: "msg-002",
     conversation_id: "conv-001",
     role: "assistant",
     content: "<response text>",
     token_count: <estimated>
   }
9. Update conversation.last_activity
10. Return response to client
```

### Flow 2: Follow-up Message in Existing Conversation

```
User sends: POST /chat { "prompt": "Tell me more about the colors", "image_id": "abc-123" }

1. Resolve session
2. Check if active conversation exists for (session_id, image_id)
   - Found: conv-001
3. Record user Message (msg-003)
4. Retrieve truncated history for conv-001:
   - msg-001: user "What do you see?"
   - msg-002: assistant "<response>"
   - msg-003: user "Tell me more about the colors"
5. Inject history into prompt context
6. Call mock_openai_chat() with augmented prompt
7. Record assistant Message (msg-004)
8. Update conversation.last_activity
9. Return response
```

### Flow 3: History Retrieval

```
Client sends: GET /chat/history?image_id=abc-123&session_id=sess-xyz

1. Look up _conversations_by_image["abc-123"] -> ["conv-001", "conv-005"]
2. Look up _conversations_by_session["sess-xyz"] -> ["conv-001", "conv-003"]
3. Intersect: ["conv-001"]
4. For each conversation, retrieve messages from _messages
5. Return:
   {
     "conversations": [{
       "conversation_id": "conv-001",
       "image_id": "abc-123",
       "session_id": "sess-xyz",
       "created_at": "...",
       "last_activity": "...",
       "messages": [msg-001, msg-002, msg-003, msg-004]
     }],
     "count": 1
   }
```

### Flow 4: Cleanup Process

```
Hourly cleanup timer fires:

1. Acquire _lock
2. current_time = datetime.utcnow()
3. For each conversation in _conversations:
   a. age = current_time - conversation.last_activity
   b. If age > (retention_days + grace_period_days) = 37 days:
      - Delete from _conversations[conversation_id]
      - Delete from _messages[conversation_id]
      - Remove conversation_id from _conversations_by_image[image_id]
      - Remove conversation_id from _conversations_by_session[session_id]
      - Clean up empty index entries
4. Release _lock
5. Log cleanup summary: "Cleaned up N conversations, M messages"
```
