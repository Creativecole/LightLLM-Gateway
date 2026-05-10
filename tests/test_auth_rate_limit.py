from fastapi.testclient import TestClient

from gateway.app import create_app
from gateway.config import ApiKeyConfig, AuthConfig, GatewayConfig, ModelConfig, ModelsConfig


def _chat_payload() -> dict[str, object]:
    return {
        "model": "mock-small",
        "messages": [{"role": "user", "content": "Hello"}],
    }


def _auth_config() -> GatewayConfig:
    return GatewayConfig(
        auth=AuthConfig(
            enabled=True,
            api_keys=[
                ApiKeyConfig(key="sk-demo", name="demo-user", rpm=2),
                ApiKeyConfig(key="sk-other", name="other-user", rpm=1),
            ],
        ),
        models=ModelsConfig(
            items=[ModelConfig(name="mock-small", backend="mock", target="mock-small")]
        ),
    )


def test_chat_completion_missing_authorization_returns_401() -> None:
    client = TestClient(create_app(_auth_config()))

    response = client.post("/v1/chat/completions", json=_chat_payload())

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing Authorization header"


def test_chat_completion_bad_authorization_format_returns_401() -> None:
    client = TestClient(create_app(_auth_config()))

    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload(),
        headers={"Authorization": "Basic sk-demo"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid Authorization header"


def test_chat_completion_invalid_api_key_returns_401() -> None:
    client = TestClient(create_app(_auth_config()))

    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload(),
        headers={"Authorization": "Bearer wrong-key"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key"


def test_chat_completion_valid_api_key_succeeds() -> None:
    client = TestClient(create_app(_auth_config()))

    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload(),
        headers={"Authorization": "Bearer sk-demo"},
    )

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "Hello from MockBackend"


def test_health_does_not_require_auth() -> None:
    client = TestClient(create_app(_auth_config()))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metrics_does_not_require_auth() -> None:
    client = TestClient(create_app(_auth_config()))

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.json() == {"metrics": {}}


def test_rate_limit_exceeded_returns_429() -> None:
    client = TestClient(create_app(_auth_config()))
    headers = {"Authorization": "Bearer sk-other"}

    first_response = client.post("/v1/chat/completions", json=_chat_payload(), headers=headers)
    second_response = client.post("/v1/chat/completions", json=_chat_payload(), headers=headers)

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert "rate limit exceeded" in second_response.json()["detail"]


def test_rate_limit_is_independent_per_api_key() -> None:
    client = TestClient(create_app(_auth_config()))

    first_response = client.post(
        "/v1/chat/completions",
        json=_chat_payload(),
        headers={"Authorization": "Bearer sk-other"},
    )
    limited_response = client.post(
        "/v1/chat/completions",
        json=_chat_payload(),
        headers={"Authorization": "Bearer sk-other"},
    )
    other_key_response = client.post(
        "/v1/chat/completions",
        json=_chat_payload(),
        headers={"Authorization": "Bearer sk-demo"},
    )

    assert first_response.status_code == 200
    assert limited_response.status_code == 429
    assert other_key_response.status_code == 200
