# LightLLM-Gateway

LightLLM-Gateway is a lightweight OpenAI-compatible gateway for local and private LLM backends. It supports Mock and Ollama backends, streaming SSE, API key auth, rate limiting, prompt cache, metrics, structured request logs, benchmark tooling, and a small dashboard.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Backend default:

```text
http://127.0.0.1:8000
```

Run checks:

```bash
bash scripts/check.sh
```

## Configuration

The project loads config in this order:

1. `LIGHTLLM_CONFIG`
2. `config.yaml`
3. `config.example.yaml`

For a fresh setup:

```bash
cp config.example.yaml config.yaml
```

Use another config file:

```bash
LIGHTLLM_CONFIG=/path/to/config.yaml python main.py
```

`config.local.yaml` is ignored by git for private local settings.

## API

Non-streaming chat completion:

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-demo" \
  -d '{
    "model": "mock-small",
    "messages": [{"role": "user", "content": "Say hello"}],
    "stream": false
  }'
```

Streaming:

```bash
curl -N http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-demo" \
  -d '{
    "model": "llama3.1",
    "messages": [{"role": "user", "content": "hello"}],
    "stream": true
  }'
```

Useful endpoints:

- `GET /api/health`
- `GET /api/models`
- `GET /api/requests`
- `GET /metrics`
- `POST /v1/chat/completions`

## Use Your Own Ollama Model

Check local models:

```bash
ollama list
```

Pull one if needed:

```bash
ollama pull llama3.1
# or
ollama pull qwen2.5:1.5b
```

The example configs include several Ollama entries you can enable after pulling the matching local model:

| Gateway model | Ollama target | Pull command |
| --- | --- | --- |
| `llama3.1` | `llama3.1` | `ollama pull llama3.1` |
| `llama3.2` | `llama3.2` | `ollama pull llama3.2` |
| `qwen2.5` | `qwen2.5:1.5b` | `ollama pull qwen2.5:1.5b` |
| `qwen2.5-0.5b` | `qwen2.5:0.5b` | `ollama pull qwen2.5:0.5b` |
| `qwen2.5-coder` | `qwen2.5-coder:1.5b` | `ollama pull qwen2.5-coder:1.5b` |
| `mistral` | `mistral` | `ollama pull mistral` |
| `gemma2` | `gemma2:2b` | `ollama pull gemma2:2b` |
| `phi3` | `phi3:mini` | `ollama pull phi3:mini` |
| `deepseek-r1` | `deepseek-r1:1.5b` | `ollama pull deepseek-r1:1.5b` |

Edit `config.yaml`:

```yaml
models:
  default: llama3.1
  items:
    - name: llama3.1
      backend: ollama
      target: llama3.1
      endpoint: http://127.0.0.1:11434
```

`name` is the Gateway-facing model name. `target` must match `ollama list`. `endpoint` is the Ollama base URL, without `/api/chat`.

## Use vLLM Backend

Start a vLLM OpenAI-compatible server:

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --host 127.0.0.1 \
  --port 8001
```

Configure LightLLM-Gateway:

```yaml
models:
  default: qwen-vllm
  items:
    - name: qwen-vllm
      backend: vllm
      target: Qwen/Qwen2.5-1.5B-Instruct
      endpoint: http://127.0.0.1:8001
```

`endpoint` is the vLLM server root URL, without `/v1/chat/completions`. `target` must match the model used to start vLLM. `name` is the Gateway-facing model name. Non-streaming responses rewrite `model` back to the Gateway-facing name.

Non-streaming request:

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-demo" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-vllm",
    "messages": [{"role": "user", "content": "hello"}],
    "stream": false
  }'
```

Streaming request:

```bash
curl -N http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-demo" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-vllm",
    "messages": [{"role": "user", "content": "hello"}],
    "stream": true
  }'
```

## Dashboard

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal. The frontend uses `VITE_GATEWAY_API_BASE`, defaulting to `http://127.0.0.1:8000`.

Production build:

```bash
cd frontend
npm run build
```

## Benchmark

```bash
python scripts/bench.py \
  --api-key sk-demo \
  --model llama3.1 \
  --concurrency 10 \
  --requests 100
```

Streaming benchmark:

```bash
python scripts/bench.py --stream --api-key sk-demo --model llama3.1
```

Reports are written to `reports/benchmark.md` by default.

## Observability

- Metrics: `GET /metrics`
- Request logs: `logs/requests.jsonl`
- Recent logs API: `GET /api/requests`

Logs record user names, not raw API keys.

## Common Errors

`Ollama returned HTTP 404`: the configured `target` model is not available locally. Run `ollama list` or `ollama pull <model>`.

`vLLM returned HTTP 404`: check that the vLLM server is running, `target` matches the served model, and `endpoint` does not include `/v1/chat/completions`.

`Missing Authorization header`: add `Authorization: Bearer sk-demo` when calling `/v1/chat/completions`.

Requests page only shows mock traffic: select an Ollama model in the Playground or change `models.default` from `mock-small`.
