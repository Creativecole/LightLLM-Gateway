# PROJECT_SPEC.md

## Project Positioning

LightLLM-Gateway is a lightweight LLM gateway for local, private, and developer-controlled model backends. It focuses on AI infrastructure primitives that are useful for both production-minded experimentation and AI Coding Agent workflows.

The gateway should expose an OpenAI-compatible API so existing tools can point at LightLLM-Gateway with minimal changes. Internally, it should provide routing, backend abstraction, streaming, authentication, rate limiting, caching, observability, request logs, and benchmark tooling.

This project starts with a deliberately small MVP. The goal is not to build a full commercial gateway immediately. The goal is to build a clean, testable foundation that future AI Coding Agents can extend safely.

## MVP Scope

The MVP includes:

- FastAPI application skeleton.
- OpenAI-compatible `/v1/chat/completions` endpoint.
- Pydantic request and response models.
- Model router interface.
- Deterministic mock backend.
- Ollama backend for non-streaming chat completion.
- SSE streaming support for `stream=true`.
- API key authentication.
- Simple in-memory rate limit.
- Prompt cache for repeated non-streaming requests.
- Metrics endpoint.
- Request logs endpoint or local log storage.
- Benchmark script for basic latency and throughput checks.
- Minimal frontend dashboard.

The MVP intentionally excludes:

- Multi-tenant billing.
- Distributed rate limiting.
- Persistent production database.
- Full OpenAI API coverage beyond chat completions.
- Complex model selection policies.
- Production-grade secret management.

## OpenAI-Compatible API

The primary endpoint is:

```text
POST /v1/chat/completions
```

The request should support the MVP subset of the OpenAI chat completions shape:

- `model`: required string.
- `messages`: required list of chat messages.
- `stream`: optional boolean, default `false`.
- `temperature`: optional number.
- `max_tokens`: optional integer.

Each message should support:

- `role`: one of `system`, `user`, `assistant`, or `tool` where practical.
- `content`: string for the MVP.

For `stream=false`, the response should follow the chat completion response shape:

- `id`
- `object`
- `created`
- `model`
- `choices`
- `usage`

For `stream=true`, the response should be sent as Server-Sent Events using OpenAI-style chat completion chunks. The stream should terminate with:

```text
data: [DONE]
```

## Model Routing

The model router maps a requested `model` string to a backend adapter.

MVP routing requirements:

- Route known test models to the mock backend.
- Route configured Ollama models to `OllamaBackend`.
- Return a clear error for unknown models.
- Keep routing logic independent from FastAPI handlers.

Future routing may include fallback chains, latency-aware routing, per-user policy, and backend health checks.

## Backend Interface

Backends should expose a small interface for:

- Non-streaming chat completion.
- Streaming chat completion.
- Model identity or backend metadata.

The API layer should not know backend-specific HTTP formats. Backend adapters translate internal request objects into backend-specific calls.

## OllamaBackend

`OllamaBackend` should call an Ollama-compatible local HTTP API.

MVP non-streaming behavior:

- Accept a chat completion request.
- Convert messages into the Ollama chat format.
- Call Ollama with `stream=false`.
- Convert the Ollama response into the OpenAI-compatible response shape.
- Use `httpx` with timeouts.
- Make base URL configurable.

MVP streaming behavior:

- Call Ollama with streaming enabled.
- Convert each Ollama event into an OpenAI-compatible SSE chunk.
- End with `data: [DONE]`.

Tests must use mocked HTTP behavior, not a real Ollama process.

## SSE Streaming

Streaming responses must use Server-Sent Events.

Requirements:

- Content type should be compatible with `text/event-stream`.
- Each emitted event should use the `data: ...` format.
- Chunks should be valid JSON except the final `[DONE]`.
- Client disconnects should not crash the app.
- Streaming code should be testable without opening a real network connection.

## Auth

MVP auth uses API keys.

Requirements:

- Accept `Authorization: Bearer <token>`.
- Reject missing or invalid tokens.
- Keep valid tokens configurable for local development.
- Do not commit real secrets.
- Tests should cover allowed and rejected requests.

## Rate Limit

MVP rate limiting is simple and in-memory.

Requirements:

- Limit requests by API key or client identity.
- Return an appropriate error when the limit is exceeded.
- Keep configuration simple.
- Tests should be deterministic and avoid real waiting where possible.

This is not intended to be production-grade distributed rate limiting.

## Prompt Cache

Prompt cache stores repeated non-streaming prompt results.

Requirements:

- Cache key should include model, messages, and relevant generation parameters.
- Cache should apply only to `stream=false` in the MVP.
- Cache should be observable through metrics.
- Cache entries may be in-memory for the MVP.
- Tests should cover hit, miss, and bypass behavior.

## Metrics

MVP metrics should expose basic runtime counters and timings.

Useful metrics:

- Total requests.
- Requests by model.
- Requests by backend.
- Error count.
- Cache hits and misses.
- Streaming request count.
- Basic latency summary.

The initial metrics endpoint can return JSON. Prometheus format can be added later if needed.

## Request Logs

Request logs should help inspect gateway behavior without storing sensitive prompt content by default.

MVP log fields:

- Request id.
- Timestamp.
- Model.
- Backend.
- Stream flag.
- Status code or error category.
- Latency.
- Cache hit flag.

Avoid logging raw prompts unless a future explicit debug mode is added.

## Benchmark

The benchmark script should provide a basic repeatable load check.

MVP benchmark behavior:

- Send a configurable number of requests.
- Support concurrency.
- Report success count, error count, latency min, max, average, and p95.
- Work against the local gateway.
- Avoid requiring a real external model for the default mock benchmark path.

## Frontend Dashboard

The MVP dashboard should be minimal and operational.

It should show:

- Basic metrics.
- Recent request logs.
- Known models or backend status if available.
- Simple refresh behavior.

The dashboard should not become a marketing landing page. It is a developer operations surface.

## MVP Completion Standard

The MVP is complete when:

- `scripts/check.sh` passes.
- `/v1/chat/completions` works for `stream=false` with the mock backend.
- `/v1/chat/completions` works for `stream=false` with mocked `OllamaBackend` tests.
- `/v1/chat/completions` works for `stream=true` through SSE.
- Auth and rate limit are enforced and tested.
- Prompt cache hit and miss behavior is tested.
- Metrics and request logs expose useful JSON.
- Benchmark script can run against the local app.
- Dashboard displays metrics and recent request logs.
- README documents setup, development workflow, and verification.
- `TASKS.md` accurately marks MVP phases as complete.
