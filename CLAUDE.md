# candidate_files Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-14

## Active Technologies
- Python 3.13 (project uses 3.13; constitution requires 3.8+ compatibility) + Flask >=2.0 (existing), Flask-Limiter (existing), Pillow (existing) (002-streaming-responses)
- In-memory (Phase 1 — no new storage needed for streaming) (002-streaming-responses)

- Python 3.13 + Flask ≥2.0, Werkzeug ≥2.0 (for secure file handling), Pillow (for image validation/metadata), Flask-Limiter (for rate limiting) (001-foundational-api)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.13: Follow standard conventions

## Recent Changes
- 002-streaming-responses: Added Python 3.13 (project uses 3.13; constitution requires 3.8+ compatibility) + Flask >=2.0 (existing), Flask-Limiter (existing), Pillow (existing)

- 001-foundational-api: Added Python 3.13 + Flask ≥2.0, Werkzeug ≥2.0 (for secure file handling), Pillow (for image validation/metadata), Flask-Limiter (for rate limiting)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
