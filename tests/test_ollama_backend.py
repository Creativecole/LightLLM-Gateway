import httpx
import pytest
from fastapi import HTTPException

from gateway.backends import ollama_backend
from gateway.backends.ollama_backend import OllamaBackend
from gateway.config import ModelConfig
from gateway.schemas import ChatCompletionRequest


class FakeAsyncClient:
    requests: list[dict[str, object]] = []

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    async def post(self, url: str, json: dict[str, object]) -> httpx.Response:
        self.requests.append({"url": url, "json": json, "timeout": self.timeout})
        return httpx.Response(
            status_code=200,
            request=httpx.Request("POST", url),
            json={
                "model": "llama3.1",
                "message": {"role": "assistant", "content": "Hello from Ollama"},
                "done": True,
                "prompt_eval_count": 3,
                "eval_count": 4,
            },
        )


class TimeoutAsyncClient(FakeAsyncClient):
    async def post(self, url: str, json: dict[str, object]) -> httpx.Response:
        raise httpx.TimeoutException("timed out")


class FakeStreamResponse:
    def __init__(self, lines: list[str]) -> None:
        self.lines = lines
        self.status_code = 200

    async def __aenter__(self) -> "FakeStreamResponse":
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    async def aiter_lines(self) -> object:
        for line in self.lines:
            yield line


class FakeStreamingAsyncClient(FakeAsyncClient):
    stream_requests: list[dict[str, object]] = []

    def stream(self, method: str, url: str, json: dict[str, object]) -> FakeStreamResponse:
        self.stream_requests.append(
            {"method": method, "url": url, "json": json, "timeout": self.timeout}
        )
        return FakeStreamResponse(
            [
                '{"message":{"role":"assistant","content":"Hel"},"done":false}',
                '{"message":{"role":"assistant","content":"lo"},"done":false}',
                '{"done":true}',
            ]
        )


@pytest.mark.asyncio
async def test_ollama_backend_sends_non_streaming_chat_request(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeAsyncClient.requests = []
    monkeypatch.setattr(ollama_backend.httpx, "AsyncClient", FakeAsyncClient)
    backend = OllamaBackend()
    request = ChatCompletionRequest(
        model="llama3.1",
        messages=[{"role": "user", "content": "Hello"}],
    )
    model = ModelConfig(
        name="llama3.1",
        backend="ollama",
        target="llama3.1",
        endpoint="http://ollama.test",
    )

    response = await backend.chat_completion(request, model)

    assert FakeAsyncClient.requests == [
        {
            "url": "http://ollama.test/api/chat",
            "json": {
                "model": "llama3.1",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            },
            "timeout": 30.0,
        }
    ]
    assert response.model == "llama3.1"
    assert response.choices[0].message.content == "Hello from Ollama"
    assert response.usage.prompt_tokens == 3
    assert response.usage.completion_tokens == 4
    assert response.usage.total_tokens == 7


@pytest.mark.asyncio
async def test_ollama_backend_timeout_becomes_504(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ollama_backend.httpx, "AsyncClient", TimeoutAsyncClient)
    backend = OllamaBackend()
    request = ChatCompletionRequest(
        model="llama3.1",
        messages=[{"role": "user", "content": "Hello"}],
    )
    model = ModelConfig(name="llama3.1", backend="ollama")

    with pytest.raises(HTTPException) as exc_info:
        await backend.chat_completion(request, model)

    assert exc_info.value.status_code == 504
    assert exc_info.value.detail == "Ollama request timed out"


@pytest.mark.asyncio
async def test_ollama_backend_streams_sse_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeStreamingAsyncClient.stream_requests = []
    monkeypatch.setattr(ollama_backend.httpx, "AsyncClient", FakeStreamingAsyncClient)
    backend = OllamaBackend()
    request = ChatCompletionRequest(
        model="llama3.1",
        messages=[{"role": "user", "content": "Hello"}],
        stream=True,
    )
    model = ModelConfig(
        name="llama3.1",
        backend="ollama",
        target="llama3.1",
        endpoint="http://ollama.test",
    )

    chunks = [chunk async for chunk in backend.stream_chat_completion(request, model)]

    assert FakeStreamingAsyncClient.stream_requests == [
        {
            "method": "POST",
            "url": "http://ollama.test/api/chat",
            "json": {
                "model": "llama3.1",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": True,
            },
            "timeout": 30.0,
        }
    ]
    assert chunks[0] == 'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n'
    assert chunks[1] == 'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'
    assert chunks[-1] == "data: [DONE]\n\n"
