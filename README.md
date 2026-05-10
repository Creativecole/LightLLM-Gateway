# LightLLM-Gateway

LightLLM-Gateway is a lightweight AI infrastructure project for building an OpenAI-compatible gateway in front of local and private LLM backends.

The project is currently in the metrics and structured request logs phase. The foundation now includes a small application factory, health endpoint, metrics endpoint, configuration loader, OpenAI-compatible chat schema, a model router, a deterministic mock backend, an Ollama backend, streaming SSE forwarding, API key auth, in-memory per-key rate limiting, prompt caching for non-streaming requests, structured JSONL request logs, project rules, phased tasks, reusable skills, and a repeatable verification script.

## Architecture

The planned MVP architecture is:

```text
Client
  |
  v
FastAPI OpenAI-compatible API
  |
  v
Auth + Rate Limit
  |
  v
Prompt Cache
  |
  v
Model Router
  |
  +--> MockBackend
  |
  +--> OllamaBackend
  |
  v
Metrics + Request Logs
```

Initial implementation is intentionally minimal. The repository currently includes the FastAPI skeleton, configuration loading, `/api/health`, `/api/info`, `/metrics`, and `/v1/chat/completions` for configured mock and Ollama models.

## Planned MVP

The MVP will include:

- OpenAI-compatible `/v1/chat/completions`.
- Model router and deterministic mock backend.
- Ollama backend for local model calls.
- SSE streaming for `stream=true`.
- API key auth and in-memory rate limit.
- Prompt cache for repeated non-streaming requests.
- Metrics, request logs, benchmark script, and dashboard.

See `PROJECT_SPEC.md` for the full project specification.

## Development Workflow

Every Agent should follow this loop:

1. Read `AGENTS.md`, `PROJECT_SPEC.md`, and `TASKS.md`.
2. Identify the active phase.
3. Use the relevant document in `skills/`.
4. Make the smallest coherent change.
5. Add or update tests for behavior changes.
6. Run `scripts/check.sh`.
7. Fix failures before handing off.

## Setup

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run Checks

Run the complete harness verification:

```bash
scripts/check.sh
```

The script runs:

- `ruff check .`
- `pytest`
- Application import check.

## Run Tests

Run tests directly with:

```bash
pytest
```

## Run the App

Start the app through the root entrypoint:

```bash
python main.py
```

Or run uvicorn directly:

```bash
uvicorn main:app --reload
```

The server reads `config.yaml` by default. The current skeleton exposes:

- `GET /api/health`
- `GET /api/info`
- `GET /metrics`
- `POST /v1/chat/completions`

## API Example

Send a non-streaming OpenAI-compatible chat completion request:

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-demo" \
  -d '{
    "model": "mock-small",
    "messages": [
      {"role": "user", "content": "Say hello"}
    ],
    "stream": false
  }'
```

The mock backend returns a deterministic assistant message:

```json
{
  "object": "chat.completion",
  "model": "mock-small",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello from MockBackend"
      },
      "finish_reason": "stop"
    }
  ]
}
```

## API Key Auth And Rate Limit

When `auth.enabled` is `true`, `/v1/chat/completions` requires:

```text
Authorization: Bearer <api_key>
```

`GET /api/health` and `GET /metrics` do not require auth.

Configure API keys and per-key request limits in `config.yaml`:

```yaml
auth:
  enabled: true
  api_keys:
    - key: sk-demo
      name: demo-user
      rpm: 60
```

`rpm` means requests per minute. The first implementation uses an in-memory sliding window per API key.

## Prompt Cache

Prompt cache is an in-memory LRU cache for repeated non-streaming chat completion requests. It only applies when `stream=false`; streaming requests always bypass the cache.

Configure it in `config.yaml`:

```yaml
cache:
  enabled: true
  max_size: 1024
```

Set `enabled: false` to disable prompt caching. `max_size` controls the maximum number of cached responses kept in memory.

The cache key is a SHA-256 hash of:

- `model`
- ordered `messages`
- `temperature`
- `top_p`

Responses include `cache_hit: false` on cache misses and `cache_hit: true` on cache hits while preserving the normal OpenAI-compatible response fields.

## Metrics

Gateway metrics are exposed as JSON:

```bash
curl -s http://127.0.0.1:8000/metrics
```

The endpoint currently reports:

- `total_requests`
- `success_requests`
- `failed_requests`
- `active_requests`
- `cache_hits`
- `cache_hit_rate`
- `avg_latency_ms`
- `avg_ttft_ms`
- `requests_per_model`
- `requests_per_backend`
- `error_rate`

`GET /metrics` is public even when API key auth is enabled.

## Structured Request Logs

Each chat completion request is written as one JSON object per line. The default log file is:

```text
logs/requests.jsonl
```

Configure the path in `config.yaml`:

```yaml
logging:
  request_logs_enabled: true
  request_log_path: logs/requests.jsonl
```

Core log fields include:

- `request_id`
- `model`
- `backend`
- `stream`
- `cache_hit`
- `ttft_ms`
- `total_latency_ms`
- `status`

Logs record the authenticated user name, not the raw API key.

## Benchmark

Run the async benchmark client against a running gateway:

```bash
python scripts/bench.py \
  --url http://localhost:8000/v1/chat/completions \
  --api-key sk-demo \
  --model llama3.1 \
  --concurrency 10 \
  --requests 100 \
  --prompt "hello"
```

Run a streaming benchmark:

```bash
python scripts/bench.py \
  --url http://localhost:8000/v1/chat/completions \
  --api-key sk-demo \
  --model llama3.1 \
  --concurrency 10 \
  --requests 100 \
  --stream \
  --prompt "hello"
```

The script prints latency, throughput, and failure-rate metrics to the terminal and writes a Markdown report to:

```text
reports/benchmark.md
```

Use `--output` to write the report somewhere else.

## Dashboard

The lightweight dashboard lives in `frontend/` and provides:

- Metrics cards from `GET /metrics`
- Recent request logs from `GET /api/requests`
- Model configuration from `GET /api/models`
- A Chat Playground for non-streaming and streaming chat completions

Start the backend first:

```bash
python main.py
```

Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

The frontend reads the backend base URL from `VITE_GATEWAY_API_BASE`. If it is not set, it defaults to:

```text
http://127.0.0.1:8000
```

Example:

```bash
VITE_GATEWAY_API_BASE=http://127.0.0.1:8000 npm run dev
```

## Ollama Backend

The gateway supports non-streaming and streaming Ollama forwarding for models configured with `backend: ollama`.

Start Ollama locally and make sure the configured model exists:

```bash
ollama serve
ollama pull llama3.1
```

With the default `config.yaml`, the gateway sends requests for `llama3.1` to:

```text
http://127.0.0.1:11434/api/chat
```

Call the gateway with an OpenAI-compatible request:

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-demo" \
  -d '{
    "model": "llama3.1",
    "messages": [
      {"role": "user", "content": "Write one short sentence about local LLMs."}
    ],
    "stream": false
}'
```

Call the streaming path with `stream=true`:

```bash
curl -N http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-demo" \
  -d '{
    "model": "llama3.1",
    "messages": [
      {"role": "user", "content": "Write one short sentence about local LLMs."}
    ],
    "stream": true
  }'
```

Streaming responses use OpenAI-compatible SSE chunks:

```text
data: {"choices":[{"delta":{"content":"..."}}]}

data: [DONE]
```

You can also run the Python streaming example:

```bash
python examples/stream_chat.py
```

Business functionality should continue to be implemented phase by phase according to `TASKS.md`.
