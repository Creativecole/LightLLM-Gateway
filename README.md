# LightLLM-Gateway

LightLLM-Gateway is a lightweight AI infrastructure project for building an OpenAI-compatible gateway in front of local and private LLM backends.

The project is currently in the OpenAI-compatible mock routing phase. The foundation now includes a small application factory, health endpoint, empty metrics endpoint, configuration loader, OpenAI-compatible chat schema, a model router, a deterministic mock backend, project rules, phased tasks, reusable skills, and a repeatable verification script.

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

Initial implementation is intentionally minimal. The repository currently includes the FastAPI skeleton, configuration loading, `/api/health`, `/api/info`, `/metrics`, and non-streaming `/v1/chat/completions` for configured mock models.

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

Business functionality should continue to be implemented phase by phase according to `TASKS.md`.
