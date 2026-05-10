import json
from pathlib import Path

from fastapi.testclient import TestClient

from gateway.app import create_app
from gateway.config import GatewayConfig, LoggingConfig, ModelConfig, ModelsConfig


def test_requests_returns_empty_list_when_log_file_is_missing(tmp_path: Path) -> None:
    app = create_app(
        GatewayConfig(logging=LoggingConfig(request_log_path=str(tmp_path / "logs" / "missing.jsonl")))
    )
    client = TestClient(app)

    response = client.get("/api/requests")

    assert response.status_code == 200
    assert response.json() == []


def test_models_returns_configured_models(tmp_path: Path) -> None:
    app = create_app(
        GatewayConfig(
            logging=LoggingConfig(request_log_path=str(tmp_path / "requests.jsonl")),
            models=ModelsConfig(
                items=[
                    ModelConfig(
                        name="llama3.1",
                        backend="ollama",
                        target="llama3.1:8b",
                        endpoint="http://127.0.0.1:11434",
                        max_context_tokens=8192,
                    )
                ]
            ),
        )
    )
    client = TestClient(app)

    response = client.get("/api/models")

    assert response.status_code == 200
    assert response.json() == [
        {
            "model": "llama3.1",
            "backend": "ollama",
            "endpoint": "http://127.0.0.1:11434",
            "model_name": "llama3.1:8b",
            "max_context_tokens": 8192,
        }
    ]


def test_requests_does_not_return_api_key_and_applies_limit(tmp_path: Path) -> None:
    log_path = tmp_path / "requests.jsonl"
    log_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "request_id": "old",
                        "time": "2026-05-10T10:00:00Z",
                        "user": "demo-user",
                        "model": "mock-small",
                        "api_key": "sk-real-secret",
                    }
                ),
                json.dumps(
                    {
                        "request_id": "new",
                        "time": "2026-05-10T11:00:00Z",
                        "user": "demo-user",
                        "model": "mock-small",
                        "key": "sk-real-secret",
                    }
                ),
            ]
        )
    )
    app = create_app(GatewayConfig(logging=LoggingConfig(request_log_path=str(log_path))))
    client = TestClient(app)

    response = client.get("/api/requests?limit=1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["request_id"] == "new"
    assert "api_key" not in data[0]
    assert "key" not in data[0]
    assert "sk-real-secret" not in response.text
