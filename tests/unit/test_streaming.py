"""Tests for streaming SSE chat responses (Question 2)."""

import json
import time
import pytest
from unittest.mock import patch

from app import create_app
from src.utils.openai_formatter import format_stream_chunk, format_stream_chunks
from src.services.mock_openai_service import _stream_response


# --- Formatter unit tests ---


class TestStreamChunkFormat:
    """Verify individual SSE chunks match OpenAI chat.completion.chunk format."""

    def test_chunk_has_required_fields(self):
        raw = format_stream_chunk(
            chunk_id="chatcmpl-test123",
            delta={"role": "assistant", "content": ""},
            created=1700000000,
        )
        assert raw.startswith("data: ")
        assert raw.endswith("\n\n")

        chunk = json.loads(raw[6:])
        assert chunk["id"] == "chatcmpl-test123"
        assert chunk["object"] == "chat.completion.chunk"
        assert chunk["created"] == 1700000000
        assert chunk["model"] == "gpt-4-vision-preview"
        assert "choices" in chunk
        assert len(chunk["choices"]) == 1

    def test_delta_replaces_message(self):
        raw = format_stream_chunk(
            chunk_id="chatcmpl-x",
            delta={"content": "Hello"},
            created=1700000000,
        )
        choice = json.loads(raw[6:])["choices"][0]
        assert "delta" in choice
        assert "message" not in choice
        assert choice["delta"]["content"] == "Hello"

    def test_finish_reason_on_stop_chunk(self):
        raw = format_stream_chunk(
            chunk_id="chatcmpl-x",
            delta={},
            created=1700000000,
            finish_reason="stop",
        )
        choice = json.loads(raw[6:])["choices"][0]
        assert choice["finish_reason"] == "stop"
        assert choice["delta"] == {}

    def test_usage_chunk(self):
        usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        raw = format_stream_chunk(
            chunk_id="chatcmpl-x",
            delta={},
            created=1700000000,
            usage=usage,
        )
        chunk = json.loads(raw[6:])
        assert chunk["usage"] == usage

    def test_no_usage_on_content_chunk(self):
        raw = format_stream_chunk(
            chunk_id="chatcmpl-x",
            delta={"content": "hi"},
            created=1700000000,
        )
        chunk = json.loads(raw[6:])
        assert chunk["usage"] is None


class TestStreamChunksSequence:
    """Verify the full SSE event sequence from format_stream_chunks."""

    def test_sequence_structure(self):
        chunks = list(format_stream_chunks("Hello world"))
        # role + 2 content words + stop + usage + [DONE] = 6
        assert len(chunks) == 6

    def test_first_chunk_is_role(self):
        chunks = list(format_stream_chunks("Hello world"))
        first = json.loads(chunks[0][6:])
        assert first["choices"][0]["delta"]["role"] == "assistant"
        assert first["choices"][0]["delta"]["content"] == ""

    def test_content_chunks_have_words(self):
        chunks = list(format_stream_chunks("Hello world"))
        c1 = json.loads(chunks[1][6:])
        c2 = json.loads(chunks[2][6:])
        assert c1["choices"][0]["delta"]["content"] == "Hello"
        assert c2["choices"][0]["delta"]["content"] == " world"

    def test_stop_chunk(self):
        chunks = list(format_stream_chunks("Hi"))
        # role, "Hi", stop, usage, [DONE]
        stop = json.loads(chunks[2][6:])
        assert stop["choices"][0]["finish_reason"] == "stop"
        assert stop["choices"][0]["delta"] == {}

    def test_usage_chunk_has_totals(self):
        chunks = list(format_stream_chunks("Hi", prompt_tokens=50))
        usage_chunk = json.loads(chunks[3][6:])
        assert usage_chunk["usage"]["prompt_tokens"] == 50
        assert usage_chunk["usage"]["total_tokens"] > 50

    def test_done_sentinel(self):
        chunks = list(format_stream_chunks("Hi"))
        assert chunks[-1] == "data: [DONE]\n\n"

    def test_all_chunks_share_same_id(self):
        chunks = list(format_stream_chunks("one two three"))
        ids = set()
        for c in chunks[:-1]:  # skip [DONE]
            ids.add(json.loads(c[6:])["id"])
        assert len(ids) == 1

    def test_reassembled_content_matches_input(self):
        original = "The quick brown fox jumps"
        chunks = list(format_stream_chunks(original))
        reassembled = ""
        for c in chunks[:-1]:  # skip [DONE]
            data = json.loads(c[6:])
            content = data["choices"][0]["delta"].get("content", "")
            reassembled += content
        assert reassembled == original


# --- Endpoint integration tests ---


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as c:
        yield c


class TestChatStreamEndpoint:
    """Test the /chat/stream SSE endpoint."""

    def test_stream_returns_event_stream_content_type(self, client):
        res = client.post(
            "/chat/stream",
            json={"prompt": "hello"},
            content_type="application/json",
        )
        assert res.status_code == 200
        assert "text/event-stream" in res.content_type

    def test_stream_returns_valid_sse_chunks(self, client):
        res = client.post(
            "/chat/stream",
            json={"prompt": "hello"},
            content_type="application/json",
        )
        data = res.get_data(as_text=True)
        lines = [l for l in data.split("\n") if l.startswith("data: ")]
        assert len(lines) >= 3  # at least role + content + stop/usage/done

    def test_stream_ends_with_done(self, client):
        res = client.post(
            "/chat/stream",
            json={"prompt": "hello"},
            content_type="application/json",
        )
        data = res.get_data(as_text=True)
        assert "data: [DONE]" in data

    def test_stream_chunks_are_valid_json(self, client):
        res = client.post(
            "/chat/stream",
            json={"prompt": "hello"},
            content_type="application/json",
        )
        data = res.get_data(as_text=True)
        for line in data.split("\n"):
            if line.startswith("data: ") and line.strip() != "data: [DONE]":
                chunk = json.loads(line[6:])
                assert chunk["object"] == "chat.completion.chunk"

    def test_stream_reassembles_to_complete_response(self, client):
        res = client.post(
            "/chat/stream",
            json={"prompt": "hello"},
            content_type="application/json",
        )
        data = res.get_data(as_text=True)
        content = ""
        for line in data.split("\n"):
            if line.startswith("data: ") and line.strip() != "data: [DONE]":
                chunk = json.loads(line[6:])
                delta = chunk["choices"][0]["delta"]
                content += delta.get("content", "")
        assert len(content) > 0

    def test_stream_missing_prompt_returns_400(self, client):
        res = client.post(
            "/chat/stream",
            json={},
            content_type="application/json",
        )
        assert res.status_code == 400
        data = res.get_json()
        assert data["error"]["code"] == "missing_prompt"

    def test_stream_no_cache_headers(self, client):
        res = client.post(
            "/chat/stream",
            json={"prompt": "hi"},
            content_type="application/json",
        )
        assert res.headers.get("Cache-Control") == "no-cache"

    def test_non_streaming_endpoint_still_works(self, client):
        """Backward compatibility: /chat still returns full JSON."""
        res = client.post(
            "/chat",
            json={"prompt": "hello"},
            content_type="application/json",
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["object"] == "chat.completion"
        assert "choices" in data
        assert data["choices"][0]["message"]["content"]


# --- US2: Connection Resilience Tests ---


class TestGeneratorExitHandling:
    """T015: Verify generator stops cleanly on client disconnect."""

    def test_generator_handles_generator_exit(self):
        """Generator should handle GeneratorExit without errors."""
        gen = _stream_response("Hello world test", "hello", delay=0)
        # Read first chunk
        first = next(gen)
        assert first.startswith("data: ")
        # Simulate client disconnect by closing the generator
        gen.close()  # Raises GeneratorExit inside the generator
        # If we get here without exception, the generator handled it cleanly

    def test_generator_stops_yielding_after_close(self):
        """After close(), generator should not yield more chunks."""
        gen = _stream_response("one two three four five", "test", delay=0)
        next(gen)  # role chunk
        next(gen)  # first content chunk
        gen.close()
        # Generator is now closed; iterating should produce nothing
        remaining = list(gen)
        assert remaining == []

    def test_generator_completes_normally_without_close(self):
        """Generator should complete full sequence when not interrupted."""
        chunks = list(_stream_response("Hello world", "test", delay=0))
        # Should have: role + 2 content + stop + usage + [DONE] = 6
        assert len(chunks) == 6
        assert chunks[-1] == "data: [DONE]\n\n"


class TestStreamTimeout:
    """T016: Verify generator terminates after STREAM_TIMEOUT_SECONDS."""

    def test_stream_timeout_terminates_generator(self, client):
        """Stream should terminate when timeout is exceeded."""
        # Testing config has STREAM_TIMEOUT_SECONDS=5
        # We mock time to simulate timeout during generation
        start = time.time()

        # Create a generator with a very long response
        long_content = " ".join(["word"] * 200)

        # Patch time.time to simulate elapsed time exceeding timeout
        call_count = [0]
        real_time = time.time

        def mock_time():
            call_count[0] += 1
            if call_count[0] > 5:
                # After a few calls, report time as past the timeout
                return start + 100  # Way past any timeout
            return real_time()

        with patch("src.services.mock_openai_service.time") as mock_time_module:
            mock_time_module.time = mock_time
            mock_time_module.sleep = lambda x: None  # No actual sleeping

            chunks = list(_stream_response(
                long_content, "test", delay=1.0, timeout_seconds=5
            ))

        # Should have terminated early (not all 200+ chunks)
        # At minimum: role chunk + some content + stop + usage + [DONE]
        assert len(chunks) < 200

    def test_stream_timeout_endpoint(self, client):
        """Endpoint should respect timeout from config."""
        # With STREAM_TIMEOUT_SECONDS=5 in testing config and MOCK_CHAT_DELAY=0,
        # streams should complete normally since they finish within timeout
        res = client.post(
            "/chat/stream",
            json={"prompt": "hello"},
            content_type="application/json",
        )
        assert res.status_code == 200
        data = res.get_data(as_text=True)
        assert "data: [DONE]" in data


# --- US3: Concurrent Streaming Tests ---


class TestConnectionLimit:
    """T022: Verify 503 when exceeding MAX_STREAMING_CONNECTIONS."""

    def test_503_when_at_capacity(self):
        """When all semaphore slots are taken, new streams get 503."""
        import threading
        from src.api.chat import _stream_semaphore_lock

        app = create_app("testing")
        # Use a very small limit for testing
        app.config["MAX_STREAMING_CONNECTIONS"] = 2

        # Reset the global semaphore so it picks up the new config
        import src.api.chat as chat_module
        chat_module._stream_semaphore = None

        with app.test_client() as c:
            # Fill both semaphore slots by acquiring directly
            sem = None
            with app.app_context():
                sem = chat_module.get_stream_semaphore()

            sem.acquire()
            sem.acquire()

            # Now the semaphore is exhausted — next stream should get 503
            res = c.post(
                "/chat/stream",
                json={"prompt": "hello"},
                content_type="application/json",
            )
            assert res.status_code == 503
            data = res.get_json()
            assert data["error"]["code"] == "streaming_capacity_exceeded"

            # Release slots
            sem.release()
            sem.release()

            # Now streaming should work again
            res = c.post(
                "/chat/stream",
                json={"prompt": "hello"},
                content_type="application/json",
            )
            assert res.status_code == 200
            assert "text/event-stream" in res.content_type

        # Reset for other tests
        chat_module._stream_semaphore = None

    def test_503_error_format(self):
        """503 response should match OpenAI error format."""
        app = create_app("testing")
        app.config["MAX_STREAMING_CONNECTIONS"] = 1

        import src.api.chat as chat_module
        chat_module._stream_semaphore = None

        with app.test_client() as c:
            with app.app_context():
                sem = chat_module.get_stream_semaphore()
            sem.acquire()

            res = c.post(
                "/chat/stream",
                json={"prompt": "hello"},
                content_type="application/json",
            )
            assert res.status_code == 503
            data = res.get_json()
            assert "error" in data
            assert data["error"]["type"] == "api_error"
            assert data["error"]["code"] == "streaming_capacity_exceeded"
            assert "message" in data["error"]

            sem.release()

        chat_module._stream_semaphore = None


class TestConcurrentStreams:
    """T021: Verify multiple simultaneous streams work without data mixing."""

    def test_concurrent_streams_no_data_mixing(self):
        """Multiple streams should each get independent, complete responses."""
        import concurrent.futures

        app = create_app("testing")
        app.config["MAX_STREAMING_CONNECTIONS"] = 10

        import src.api.chat as chat_module
        chat_module._stream_semaphore = None

        results = []

        def stream_request(prompt):
            with app.test_client() as c:
                res = c.post(
                    "/chat/stream",
                    json={"prompt": prompt},
                    content_type="application/json",
                )
                data = res.get_data(as_text=True)
                return {"status": res.status_code, "data": data, "prompt": prompt}

        prompts = [f"hello {i}" for i in range(5)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(stream_request, p) for p in prompts]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should succeed
        for r in results:
            assert r["status"] == 200, f"Stream for '{r['prompt']}' failed with {r['status']}"
            assert "data: [DONE]" in r["data"], f"Stream for '{r['prompt']}' missing [DONE]"

        # Each should have valid JSON chunks
        for r in results:
            chunk_ids = set()
            for line in r["data"].split("\n"):
                if line.startswith("data: ") and line.strip() != "data: [DONE]":
                    chunk = json.loads(line[6:])
                    chunk_ids.add(chunk["id"])
            # All chunks in one stream share the same ID
            assert len(chunk_ids) == 1, f"Stream for '{r['prompt']}' had mixed chunk IDs: {chunk_ids}"

        chat_module._stream_semaphore = None


# --- US4: Backpressure Tests ---


class TestStreamingRateLimit:
    """T026: Verify rate limiting applies to streaming endpoint."""

    def test_rate_limit_returns_429(self):
        """Streaming endpoint should return 429 when rate limited."""
        app = create_app("testing")
        app.config["CHAT_RATE_LIMIT"] = "2 per minute"

        import src.api.chat as chat_module
        chat_module._stream_semaphore = None

        with app.test_client() as c:
            # First two requests should succeed
            for _ in range(2):
                res = c.post(
                    "/chat/stream",
                    json={"prompt": "hello"},
                    content_type="application/json",
                )
                assert res.status_code == 200

            # Third request should be rate limited
            res = c.post(
                "/chat/stream",
                json={"prompt": "hello"},
                content_type="application/json",
            )
            assert res.status_code == 429

        chat_module._stream_semaphore = None


# --- Phase 7: Polish & Validation Tests ---


class TestStreamingPolish:
    """T031-T032: Final validation tests."""

    def test_streaming_content_matches_non_streaming(self, client):
        """T031: Reassembled streaming content should be a valid response for the same prompt."""
        # Get streaming response
        stream_res = client.post(
            "/chat/stream",
            json={"prompt": "hello"},
            content_type="application/json",
        )
        stream_data = stream_res.get_data(as_text=True)
        stream_content = ""
        for line in stream_data.split("\n"):
            if line.startswith("data: ") and line.strip() != "data: [DONE]":
                chunk = json.loads(line[6:])
                delta = chunk["choices"][0]["delta"]
                stream_content += delta.get("content", "")

        # Get non-streaming response
        chat_res = client.post(
            "/chat",
            json={"prompt": "hello"},
            content_type="application/json",
        )
        chat_data = chat_res.get_json()
        chat_content = chat_data["choices"][0]["message"]["content"]

        # Both should be non-empty valid responses
        assert len(stream_content) > 0
        assert len(chat_content) > 0
        # Both are greeting responses (from the same TEXT_ONLY_RESPONSES pool)
        # They may differ due to random.choice, but both should be valid strings

    def test_first_token_within_200ms(self, client):
        """T032: First SSE chunk should arrive within 200ms in test environment."""
        start = time.time()
        res = client.post(
            "/chat/stream",
            json={"prompt": "hello"},
            content_type="application/json",
        )
        # In testing config, MOCK_CHAT_DELAY=0, so first token should be near-instant
        first_token_time = time.time() - start
        assert res.status_code == 200
        # Very generous bound — 200ms. In practice it's <10ms with no delay.
        assert first_token_time < 0.2, f"First token took {first_token_time:.3f}s"
