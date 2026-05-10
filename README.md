# LightLLM-Gateway

LightLLM-Gateway is a lightweight AI infrastructure project for building an OpenAI-compatible gateway in front of local and private LLM backends.

The project is currently in the API key auth and rate limit phase. The foundation now includes a small application factory, health endpoint, empty metrics endpoint, configuration loader, OpenAI-compatible chat schema, a model router, a deterministic mock backend, an Ollama backend, streaming SSE forwarding, API key auth, in-memory per-key rate limiting, project rules, phased tasks, reusable skills, and a repeatable verification script.

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
