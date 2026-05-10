from fastapi.testclient import TestClient

from gateway.app import create_app


def test_chat_completion_returns_mock_response() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "mock-small",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "mock-small"
    assert data["choices"][0]["message"] == {
        "role": "assistant",
        "content": "Hello from MockBackend",
    }


def test_chat_completion_unknown_model_returns_404() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "missing-model",
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Model not found: missing-model"


def test_chat_completion_response_schema_fields_exist() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "mock-small",
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )

    data = response.json()
    assert response.status_code == 200
    assert data["id"].startswith("chatcmpl-")
    assert data["object"] == "chat.completion"
    assert isinstance(data["created"], int)
    assert "choices" in data
    assert "usage" in data


def test_chat_completion_stream_true_is_rejected() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "mock-small",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": True,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "stream=true is not supported yet"
