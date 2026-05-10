# TASKS.md

Task status legend:

- `[ ]` Not started
- `[~]` In progress
- `[x]` Complete

## Phase 0: Harness Scaffold

- [x] Create `AGENTS.md` with Agent rules and workflow.
- [x] Create `PROJECT_SPEC.md` with MVP specification.
- [x] Create `TASKS.md` with phased task plan.
- [x] Create `skills/` workflow documents.
- [x] Create `scripts/check.sh`.
- [x] Create `requirements.txt`.
- [x] Create initial `README.md`.
- [x] Add minimal importable app placeholder for harness verification.

## Phase 1: FastAPI App Skeleton

- [x] Create FastAPI app factory.
- [x] Add health endpoint.
- [x] Add version or metadata endpoint.
- [x] Add application settings module.
- [x] Add tests for app startup and health endpoint.

## Phase 2: OpenAI-Compatible Schema

- [x] Define chat completion request schema.
- [x] Define chat completion response schema.
- [x] Define chat completion chunk schema.
- [x] Validate required fields and common invalid inputs.
- [x] Add schema tests.

## Phase 3: Model Router + Mock Backend

- [x] Define backend protocol or base interface.
- [x] Implement deterministic mock backend.
- [x] Implement model router.
- [x] Wire mock backend to `/v1/chat/completions`.
- [x] Add routing and mock response tests.

## Phase 4: Ollama Backend `stream=false`

- [ ] Add Ollama backend configuration.
- [ ] Implement non-streaming Ollama HTTP call with `httpx`.
- [ ] Translate OpenAI-style request to Ollama chat request.
- [ ] Translate Ollama response to OpenAI-compatible response.
- [ ] Add mocked HTTP tests.

## Phase 5: SSE `stream=true`

- [ ] Implement SSE formatting utility.
- [ ] Add streaming backend interface method.
- [ ] Implement mock backend streaming.
- [ ] Implement Ollama streaming translation.
- [ ] Add tests for SSE chunks and `[DONE]`.

## Phase 6: Auth + Rate Limit

- [ ] Add API key auth dependency or middleware.
- [ ] Add local config for valid API keys.
- [ ] Implement in-memory rate limiter.
- [ ] Apply auth and rate limit to chat completions.
- [ ] Add tests for valid auth, missing auth, invalid auth, and limit exceeded.

## Phase 7: Prompt Cache

- [ ] Implement cache key generation.
- [ ] Implement in-memory prompt cache.
- [ ] Apply cache to non-streaming requests.
- [ ] Add cache metrics.
- [ ] Add tests for cache hit, miss, and streaming bypass.

## Phase 8: Metrics + Request Logs

- [ ] Add metrics collector.
- [ ] Add JSON metrics endpoint.
- [ ] Add request log model.
- [ ] Add recent request logs endpoint.
- [ ] Add tests for metrics and logs.

## Phase 9: Benchmark Script

- [ ] Create benchmark script.
- [ ] Support request count and concurrency flags.
- [ ] Report success, errors, and latency summary.
- [ ] Default to mock model path.
- [ ] Document benchmark usage.

## Phase 10: Frontend Dashboard

- [ ] Add minimal dashboard route or frontend app.
- [ ] Display metrics.
- [ ] Display recent request logs.
- [ ] Add refresh behavior.
- [ ] Add basic dashboard tests where practical.
