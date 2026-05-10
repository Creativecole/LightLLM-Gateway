# Skill: Write Tests

Use this skill whenever behavior changes.

## Goal

Add focused tests that prove the intended behavior and protect against regressions.

## Steps

1. Identify the behavior under test.
2. Prefer unit tests for pure routing, schema, cache, and rate limit logic.
3. Use FastAPI test clients for API contract tests.
4. Use `pytest-asyncio` for async behavior when needed.
5. Mock external HTTP calls.
6. Test both success and failure cases.
7. Keep test names descriptive.

## Required Test Areas By Phase

- App skeleton: startup and health.
- Schema: valid and invalid request shapes.
- Router: known model and unknown model.
- Mock backend: deterministic output.
- Ollama backend: mocked HTTP request and response translation.
- Streaming: SSE chunk format and `[DONE]`.
- Auth: missing, invalid, and valid token.
- Rate limit: allowed request and exceeded request.
- Cache: hit, miss, and streaming bypass.
- Metrics and logs: counters and recorded request metadata.

## Rules

- Do not require a real Ollama server in tests.
- Do not weaken tests to pass.
- Do not hide failing assertions behind broad exception handling.
