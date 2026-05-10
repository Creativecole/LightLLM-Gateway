import json
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi.testclient import TestClient

from gateway.app import create_app
from gateway.config import CacheConfig, GatewayConfig, LoggingConfig, ModelConfig, ModelsConfig
from gateway.schemas import ChatCompletionChoice, ChatCompletionRequest, ChatCompletionResponse, Usage
from gateway.sse import format_chat_delta, format_done


class FailingRouter:
    def backend_name_for_model(self, model: str) -> str:
        return "mock"

    async def chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        raise RuntimeError("backend exploded")

    async def stream_chat_completion(self, request: ChatCompletionRequest) -> AsyncIterator[str]:
        raise RuntimeError("stream exploded")
        yield ""


class StreamingRouter:
    def backend_name_for_model(self, model: str) -> str:
        return "mock"

    async def chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        return _response(request.model, "non-stream")

    async def stream_chat_completion(self, request: ChatCompletionRequest) -> AsyncIterator[str]:
        yield format_chat_delta("hello")
        yield format_done()


def _client(tmp_path: Path, *, cache_enabled: bool = True) -> TestClient:
    config = GatewayConfig(
        cache=CacheConfig(enabled=cache_enabled),
        logging=LoggingConfig(request_log_path=str(tmp_path / "missing" / "requests.jsonl")),
        models=ModelsConfig(
            items=[ModelConfig(name="mock-small", backend="mock", target="mock-small")]
        ),
    )
    return TestClient(create_app(config), raise_server_exceptions=False)


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "model": "mock-small",
        "messages": [{"role": "user", "content": "Hello"}],
    }
    payload.update(overrides)
    return payload


def _response(model: str, content: str) -> ChatCompletionResponse:
    return ChatCompletionResponse(
        id="chatcmpl-test",
        created=1,
        model=model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message={"role": "assistant", "content": content},
                finish_reason="stop",
            )
        ],
        usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )


def _read_log_records(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_metrics_endpoint_returns_expected_fields(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get("/metrics")

    assert response.status_code == 200
    data = response.json()
    for field in [
        "total_requests",
        "success_requests",
        "failed_requests",
        "active_requests",
        "cache_hits",
        "cache_hit_rate",
        "avg_latency_ms",
        "avg_ttft_ms",
        "requests_per_model",
        "requests_per_backend",
        "error_rate",
    ]:
        assert field in data


def test_non_streaming_request_updates_metrics_and_writes_json_log(tmp_path: Path) -> None:
    client = _client(tmp_path)
    log_path = tmp_path / "missing" / "requests.jsonl"

    response = client.post("/v1/chat/completions", json=_payload())
    metrics = client.get("/metrics").json()
    records = _read_log_records(log_path)

    assert response.status_code == 200
    assert metrics["total_requests"] == 1
    assert metrics["success_requests"] == 1
    assert metrics["requests_per_model"] == {"mock-small": 1}
    assert metrics["requests_per_backend"] == {"mock": 1}
    assert len(records) == 1
    assert records[0]["request_id"]
    assert records[0]["model"] == "mock-small"
    assert records[0]["backend"] == "mock"
    assert records[0]["stream"] is False
    assert records[0]["cache_hit"] is False
    assert records[0]["status"] == "success"
    assert records[0]["error"] is None
    assert "sk-demo" not in log_path.read_text()


def test_cache_hit_increments_cache_hits_metric(tmp_path: Path) -> None:
    client = _client(tmp_path)

    client.post("/v1/chat/completions", json=_payload())
    response = client.post("/v1/chat/completions", json=_payload())
    metrics = client.get("/metrics").json()

    assert response.json()["cache_hit"] is True
    assert metrics["total_requests"] == 2
    assert metrics["cache_hits"] == 1


def test_failed_request_increments_failed_requests(tmp_path: Path) -> None:
    client = _client(tmp_path, cache_enabled=False)
    client.app.state.model_router = FailingRouter()
    log_path = tmp_path / "missing" / "requests.jsonl"

    response = client.post("/v1/chat/completions", json=_payload())
    metrics = client.get("/metrics").json()
    records = _read_log_records(log_path)

    assert response.status_code == 500
    assert metrics["failed_requests"] == 1
    assert metrics["error_rate"] == 1
    assert records[0]["status"] == "failed"
    assert records[0]["error"] == "backend exploded"


def test_streaming_request_updates_metrics_and_log(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.app.state.model_router = StreamingRouter()
    log_path = tmp_path / "missing" / "requests.jsonl"

    response = client.post("/v1/chat/completions", json=_payload(stream=True))
    metrics = client.get("/metrics").json()
    records = _read_log_records(log_path)

    assert response.status_code == 200
    assert response.text.endswith("data: [DONE]\n\n")
    assert metrics["total_requests"] == 1
    assert metrics["success_requests"] == 1
    assert metrics["avg_ttft_ms"] >= 0
    assert records[0]["stream"] is True
    assert records[0]["ttft_ms"] is not None
    assert records[0]["total_latency_ms"] >= records[0]["ttft_ms"]


def test_request_log_directory_is_created(tmp_path: Path) -> None:
    client = _client(tmp_path)
    log_path = tmp_path / "missing" / "requests.jsonl"

    client.post("/v1/chat/completions", json=_payload())

    assert log_path.exists()
