from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

from gateway.app import create_app
from gateway.cache.prompt_cache import PromptCache, build_cache_key
from gateway.config import CacheConfig, GatewayConfig
from gateway.schemas import ChatCompletionChoice, ChatCompletionRequest, ChatCompletionResponse, Usage
from gateway.sse import format_chat_delta, format_done


class CountingRouter:
    def __init__(self) -> None:
        self.chat_calls = 0
        self.stream_calls = 0

    async def chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        self.chat_calls += 1
        return ChatCompletionResponse(
            id=f"chatcmpl-{self.chat_calls}",
            created=1,
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message={
                        "role": "assistant",
                        "content": f"call-{self.chat_calls}",
                    },
                    finish_reason="stop",
                )
            ],
            usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

    async def stream_chat_completion(self, request: ChatCompletionRequest) -> AsyncIterator[str]:
        self.stream_calls += 1
        yield format_chat_delta(f"stream-call-{self.stream_calls}")
        yield format_done()


def _create_test_client(cache_enabled: bool = True, max_size: int = 1024) -> tuple[TestClient, CountingRouter]:
    app = create_app(GatewayConfig(cache=CacheConfig(enabled=cache_enabled, max_size=max_size)))
    router = CountingRouter()
    app.state.model_router = router
    return TestClient(app), router


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "model": "mock-small",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False,
    }
    payload.update(overrides)
    return payload


def test_same_non_streaming_request_hits_cache_on_second_call() -> None:
    client, router = _create_test_client()

    first_response = client.post("/v1/chat/completions", json=_payload())
    second_response = client.post("/v1/chat/completions", json=_payload())

    assert router.chat_calls == 1
    assert first_response.json()["cache_hit"] is False
    assert second_response.json()["cache_hit"] is True
    assert second_response.json()["choices"][0]["message"]["content"] == "call-1"


def test_streaming_request_does_not_use_cache() -> None:
    client, router = _create_test_client()

    first_response = client.post("/v1/chat/completions", json=_payload(stream=True))
    second_response = client.post("/v1/chat/completions", json=_payload(stream=True))

    assert router.chat_calls == 0
    assert router.stream_calls == 2
    assert "cache_hit" not in first_response.text
    assert "stream-call-1" in first_response.text
    assert "stream-call-2" in second_response.text


def test_different_models_do_not_share_cache() -> None:
    client, router = _create_test_client()

    client.post("/v1/chat/completions", json=_payload(model="mock-small"))
    client.post("/v1/chat/completions", json=_payload(model="mock-large"))

    assert router.chat_calls == 2


def test_different_messages_do_not_share_cache() -> None:
    client, router = _create_test_client()

    client.post("/v1/chat/completions", json=_payload(messages=[{"role": "user", "content": "One"}]))
    client.post("/v1/chat/completions", json=_payload(messages=[{"role": "user", "content": "Two"}]))

    assert router.chat_calls == 2


def test_different_temperature_and_top_p_do_not_share_cache() -> None:
    client, router = _create_test_client()

    client.post("/v1/chat/completions", json=_payload(temperature=0.1, top_p=0.9))
    client.post("/v1/chat/completions", json=_payload(temperature=0.2, top_p=0.9))
    client.post("/v1/chat/completions", json=_payload(temperature=0.2, top_p=0.8))

    assert router.chat_calls == 3


def test_cache_disabled_does_not_cache() -> None:
    client, router = _create_test_client(cache_enabled=False)

    first_response = client.post("/v1/chat/completions", json=_payload())
    second_response = client.post("/v1/chat/completions", json=_payload())

    assert router.chat_calls == 2
    assert "cache_hit" not in first_response.json()
    assert "cache_hit" not in second_response.json()


def test_prompt_cache_max_size_evicts_oldest_entry() -> None:
    cache = PromptCache(max_size=1)
    first_request = ChatCompletionRequest.model_validate(_payload(messages=[{"role": "user", "content": "One"}]))
    second_request = ChatCompletionRequest.model_validate(_payload(messages=[{"role": "user", "content": "Two"}]))
    first_key = build_cache_key(first_request)
    second_key = build_cache_key(second_request)

    cache.set(first_key, {"id": "first"})
    cache.set(second_key, {"id": "second"})

    assert cache.get(first_key) is None
    assert cache.get(second_key) == {"id": "second"}


def test_cache_key_is_stable_and_sensitive_to_message_order() -> None:
    first_request = ChatCompletionRequest.model_validate(
        _payload(
            messages=[
                {"role": "system", "content": "A"},
                {"role": "user", "content": "B"},
            ]
        )
    )
    same_request = ChatCompletionRequest.model_validate(first_request.model_dump(mode="json"))
    reordered_request = ChatCompletionRequest.model_validate(
        _payload(
            messages=[
                {"role": "user", "content": "B"},
                {"role": "system", "content": "A"},
            ]
        )
    )

    assert build_cache_key(first_request) == build_cache_key(same_request)
    assert build_cache_key(first_request) != build_cache_key(reordered_request)
