"""vLLM OpenAI-compatible backend adapter."""

import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
from fastapi import HTTPException

from gateway.backends.base import BaseBackend
from gateway.config import ModelConfig
from gateway.schemas import ChatCompletionRequest, ChatCompletionResponse
from gateway.sse import format_done, format_error

DEFAULT_TIMEOUT_SECONDS = 60.0
LOGGER = logging.getLogger(__name__)


class VLLMBackend(BaseBackend):
    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        model: ModelConfig,
    ) -> ChatCompletionResponse:
        endpoint = _endpoint(model)
        url = _chat_url(endpoint)
        payload = _build_payload(request, model, stream=False)

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=504, detail=f"vLLM request timed out: {endpoint}") from exc
        except httpx.HTTPStatusError as exc:
            raise _status_error(exc, endpoint=endpoint, target=_target(model)) from exc
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"vLLM endpoint unreachable: {endpoint}; reason: {exc}",
            ) from exc

        data = response.json()
        if isinstance(data, dict):
            data["model"] = request.model
        return ChatCompletionResponse.model_validate(data)

    async def stream_chat_completion(
        self,
        request: ChatCompletionRequest,
        model: ModelConfig,
    ) -> AsyncIterator[str]:
        endpoint = _endpoint(model)
        url = _chat_url(endpoint)
        payload = _build_payload(request, model, stream=True)
        saw_done = False

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        chunk = _normalize_sse_line(line)
                        if chunk == "data: [DONE]\n\n":
                            saw_done = True
                        yield chunk
        except httpx.TimeoutException:
            LOGGER.exception("vLLM streaming request timed out")
            yield format_error(f"vLLM request timed out: {endpoint}")
        except httpx.HTTPStatusError as exc:
            LOGGER.exception("vLLM streaming request returned HTTP %s", exc.response.status_code)
            yield format_error(_status_error_detail(exc, endpoint=endpoint, target=_target(model)))
        except httpx.RequestError as exc:
            LOGGER.exception("vLLM streaming request failed")
            yield format_error(f"vLLM endpoint unreachable: {endpoint}; reason: {exc}")

        if not saw_done:
            yield format_done()


def _endpoint(model: ModelConfig) -> str:
    if not model.endpoint:
        raise HTTPException(status_code=400, detail=f"Missing vLLM endpoint for model: {model.name}")
    return model.endpoint.rstrip("/")


def _target(model: ModelConfig) -> str:
    return model.target or model.name


def _chat_url(endpoint: str) -> str:
    return f"{endpoint}/v1/chat/completions"


def _build_payload(
    request: ChatCompletionRequest,
    model: ModelConfig,
    *,
    stream: bool,
) -> dict[str, Any]:
    payload = request.model_dump(mode="json", exclude_none=True)
    payload["model"] = _target(model)
    payload["stream"] = stream
    return payload


def _status_error(exc: httpx.HTTPStatusError, *, endpoint: str, target: str) -> HTTPException:
    return HTTPException(
        status_code=502,
        detail=_status_error_detail(exc, endpoint=endpoint, target=target),
    )


def _status_error_detail(exc: httpx.HTTPStatusError, *, endpoint: str, target: str) -> str:
    status_code = exc.response.status_code
    response_text = exc.response.text[:500]
    if status_code == 404:
        return (
            f"vLLM returned HTTP 404 from {endpoint}. Check that the vLLM server is running, "
            f"target model '{target}' is correct, and endpoint does not include /v1/chat/completions."
        )
    return f"vLLM returned HTTP {status_code} from {endpoint}: {response_text}"


def _normalize_sse_line(line: str) -> str:
    if line.startswith("data:"):
        return f"{line}\n\n"
    return f"data: {line}\n\n"
