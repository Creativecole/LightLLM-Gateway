import httpx
import pytest
from fastapi import HTTPException

from gateway.backends import vllm_backend
from gateway.backends.vllm_backend import VLLMBackend
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
                "id": "chatcmpl-vllm",
                "object": "chat.completion",
                "created": 1,
                "model": "Qwen/Qwen2.5-1.5B-Instruct",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Hello from vLLM"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
            },
        )


class NotFoundAsyncClient(FakeAsyncClient):
    async def post(self, url: str, json: dict[str, object]) -> httpx.Response:
        response = httpx.Response(
            status_code=404,
            request=httpx.Request("POST", url),
            text="model not found",
        )
        response.raise_for_status()
        return response


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


class StreamingAsyncClient(FakeAsyncClient):
    stream_requests: list[dict[str, object]] = []
    lines = [
        'data: {"choices":[{"delta":{"content":"Hel"}}]}',
        'data: {"choices":[{"delta":{"content":"lo"}}]}',
    ]

    def stream(self, method: str, url: str, json: dict[str, object]) -> FakeStreamResponse:
        self.stream_requests.append(
            {"method": method, "url": url, "json": json, "timeout": self.timeout}
        )
        return FakeStreamResponse(self.lines)


def _request(stream: bool = False) -> ChatCompletionRequest:
    return ChatCompletionRequest(
        model="qwen-vllm",
        messages=[{"role": "user", "content": "hello"}],
        stream=stream,
        temperature=0.7,
        top_p=1.0,
    )


def _model() -> ModelConfig:
    return ModelConfig(
        name="qwen-vllm",
        backend="vllm",
        target="Qwen/Qwen2.5-1.5B-Instruct",
        endpoint="http://vllm.test",
    )


@pytest.mark.asyncio
async def test_vllm_backend_non_streaming_forwards_openai_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.requests = []
    monkeypatch.setattr(vllm_backend.httpx, "AsyncClient", FakeAsyncClient)

    response = await VLLMBackend().chat_completion(_request(), _model())

    assert FakeAsyncClient.requests == [
        {
            "url": "http://vllm.test/v1/chat/completions",
            "json": {
                "model": "Qwen/Qwen2.5-1.5B-Instruct",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": False,
                "temperature": 0.7,
                "top_p": 1.0,
            },
            "timeout": 60.0,
        }
    ]
    assert response.model == "qwen-vllm"
    assert response.choices[0].message.content == "Hello from vLLM"


@pytest.mark.asyncio
async def test_vllm_backend_404_detail_mentions_endpoint_and_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(vllm_backend.httpx, "AsyncClient", NotFoundAsyncClient)

    with pytest.raises(HTTPException) as exc_info:
        await VLLMBackend().chat_completion(_request(), _model())

    assert exc_info.value.status_code == 502
    detail = exc_info.value.detail
    assert "http://vllm.test" in detail
    assert "Qwen/Qwen2.5-1.5B-Instruct" in detail
    assert "endpoint does not include /v1/chat/completions" in detail


@pytest.mark.asyncio
async def test_vllm_backend_streams_sse_and_appends_done(monkeypatch: pytest.MonkeyPatch) -> None:
    StreamingAsyncClient.stream_requests = []
    StreamingAsyncClient.lines = [
        'data: {"choices":[{"delta":{"content":"Hel"}}]}',
        'data: {"choices":[{"delta":{"content":"lo"}}]}',
    ]
    monkeypatch.setattr(vllm_backend.httpx, "AsyncClient", StreamingAsyncClient)

    chunks = [chunk async for chunk in VLLMBackend().stream_chat_completion(_request(True), _model())]

    assert StreamingAsyncClient.stream_requests == [
        {
            "method": "POST",
            "url": "http://vllm.test/v1/chat/completions",
            "json": {
                "model": "Qwen/Qwen2.5-1.5B-Instruct",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": True,
                "temperature": 0.7,
                "top_p": 1.0,
            },
            "timeout": 60.0,
        }
    ]
    assert chunks == [
        'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n',
        'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n',
        "data: [DONE]\n\n",
    ]


@pytest.mark.asyncio
async def test_vllm_backend_does_not_duplicate_done(monkeypatch: pytest.MonkeyPatch) -> None:
    StreamingAsyncClient.lines = [
        'data: {"choices":[{"delta":{"content":"Hi"}}]}',
        "data: [DONE]",
    ]
    monkeypatch.setattr(vllm_backend.httpx, "AsyncClient", StreamingAsyncClient)

    chunks = [chunk async for chunk in VLLMBackend().stream_chat_completion(_request(True), _model())]

    assert chunks.count("data: [DONE]\n\n") == 1
    assert chunks[-1] == "data: [DONE]\n\n"
