# Research: Streaming Chat Responses

**Feature**: 002-streaming-responses
**Date**: 2026-02-16

## R1: Client Disconnect Detection in Flask SSE

**Decision**: Use `GeneratorExit` exception handling with `try/finally` in the streaming generator.

**Rationale**: Flask/Werkzeug raises `GeneratorExit` when a generator is closed, which happens when the client disconnects and WSGI attempts to write to the closed socket. This is the standard Python generator cleanup mechanism and requires no additional dependencies. Since our mock streaming responses are short-lived (not long-polling), the generator naturally completes quickly. For longer streams, a heartbeat comment line (`: heartbeat\n\n`) can force disconnect detection.

**Alternatives considered**:
- `Response.call_on_close()`: Only runs after the full response is sent, not useful for mid-stream detection.
- Werkzeug `ClientDisconnected` exception: Not consistently raised across WSGI servers.
- Periodic polling with `request.environ.get('werkzeug.server.shutdown')`: Not a standard API.

## R2: Concurrent Connection Limiting

**Decision**: Use `threading.BoundedSemaphore` with non-blocking acquire at the endpoint level, and release in the generator's `finally` block.

**Rationale**: `BoundedSemaphore` is purpose-built for limiting concurrent access to a resource pool. Unlike a plain counter with a lock, it prevents accidental over-release (which `Semaphore` alone does not). Non-blocking acquire (`acquire(blocking=False)`) allows immediate 503 response when at capacity rather than queuing. The `finally` block ensures the semaphore is released even on exceptions or disconnects.

**Alternatives considered**:
- `threading.Lock` with manual counter: More code, same result, more error-prone.
- `threading.Semaphore` (unbounded): Allows accidental over-release if release is called more times than acquire.
- Middleware-based counter: Adds complexity; the semaphore pattern is simpler and self-contained.

## R3: Per-Connection Stream Timeout

**Decision**: Track elapsed time inside the generator loop using `time.time()` and break when the timeout threshold is exceeded.

**Rationale**: Simple, cross-platform, and predictable. The generator loop naturally checks elapsed time on each iteration (each chunk yield). No external threads, signals, or timers needed. Works correctly in Flask's threaded WSGI model.

**Alternatives considered**:
- `signal.alarm()`: Unix-only, not thread-safe, incompatible with threaded WSGI servers.
- `threading.Timer`: Adds a separate thread per connection, requires coordination to cancel, risk of timer outliving the connection.
- WSGI server timeout: Not granular enough — applies to the entire request, not specifically to the streaming phase.

## R4: OpenAI SSE Chunk Format

**Decision**: Match the OpenAI Chat Completions API streaming format exactly — `chat.completion.chunk` objects with `delta` instead of `message`.

**Rationale**: Constitution Principle II (OpenAI API Compatibility) requires mock responses to be indistinguishable from production. The format is well-documented and widely adopted as a de facto standard.

**Key format details**:
- Object type: `chat.completion.chunk` (not `chat.completion`)
- Choice field: `delta` (not `message`)
- Sequence: role chunk → content chunks → stop chunk → usage chunk → `[DONE]`
- All chunks share the same `id` and `created` timestamp
- Wire format: `data: {JSON}\n\n` per event, terminated by `data: [DONE]\n\n`

**Source**: OpenAI API documentation — Chat Completions streaming reference.
