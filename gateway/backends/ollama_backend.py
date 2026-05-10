"""Ollama backend adapter."""

import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
from fastapi import HTTPException

from gateway.backends.base import BaseBackend
from gateway.config import ModelConfig
from gateway.schemas import ChatCompletionChoice, ChatCompletionRequest, ChatCompletionResponse, Usage
from gateway.sse import format_chat_delta, format_done, format_error

DEFAULT_OLLAMA_ENDPOINT = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT_SECONDS = 30.0
LOGGER = logging.getLogger(__name__)


class OllamaBackend(BaseBackend):
    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        model: ModelConfig,
    ) -> ChatCompletionResponse:
        endpoint = (model.endpoint or DEFAULT_OLLAMA_ENDPOINT).rstrip("/")
        payload = {
            "model": model.target or model.name,
            "messages": [
                {"role": message.role, "content": message.content} for message in request.messages
            ],
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
                response = await client.post(f"{endpoint}/api/chat", json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=504, detail="Ollama request timed out") from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            raise HTTPException(
                status_code=502,
                detail=f"Ollama returned HTTP {status_code}",
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail="Ollama request failed") from exc

        data = response.json()
        message = _extract_message(data)
        prompt_tokens = int(data.get("prompt_eval_count") or 0)
        completion_tokens = int(data.get("eval_count") or len(message["content"].split()))

        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=message,
                    finish_reason="stop" if data.get("done", True) else None,
                )
            ],
            usage=Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )

    async def stream_chat_completion(
        self,
        request: ChatCompletionRequest,
        model: ModelConfig,
    ) -> AsyncIterator[str]:
        endpoint = (model.endpoint or DEFAULT_OLLAMA_ENDPOINT).rstrip("/")
        payload = _build_ollama_payload(request, model, stream=True)
        request_started_at = time.monotonic()
        first_chunk_at: float | None = None

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
                async with client.stream("POST", f"{endpoint}/api/chat", json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        content = _extract_stream_content(data)
                        if content:
                            if first_chunk_at is None:
                                first_chunk_at = time.monotonic()
                                _ttft_seconds = first_chunk_at - request_started_at
                                # TODO: record _ttft_seconds in metrics/request logs in Phase 8.
                            yield format_chat_delta(content)
                        if data.get("done") is True:
                            break
        except httpx.TimeoutException:
            LOGGER.exception("Ollama streaming request timed out")
            yield format_error("Ollama streaming request timed out")
        except httpx.HTTPStatusError as exc:
            LOGGER.exception("Ollama streaming request returned HTTP %s", exc.response.status_code)
            yield format_error(f"Ollama returned HTTP {exc.response.status_code}")
        except httpx.RequestError:
            LOGGER.exception("Ollama streaming request failed")
            yield format_error("Ollama streaming request failed")
        except json.JSONDecodeError:
            LOGGER.exception("Ollama streaming response contained invalid JSON")
            yield format_error("Ollama streaming response contained invalid JSON")

        yield format_done()


def _extract_message(data: dict[str, Any]) -> dict[str, str]:
    message = data.get("message")
    if not isinstance(message, dict):
        raise HTTPException(status_code=502, detail="Ollama response missing message")

    role = message.get("role") or "assistant"
    content = message.get("content")
    if not isinstance(content, str):
        raise HTTPException(status_code=502, detail="Ollama response missing message content")

    return {"role": role, "content": content}


def _build_ollama_payload(
    request: ChatCompletionRequest,
    model: ModelConfig,
    *,
    stream: bool,
) -> dict[str, object]:
    return {
        "model": model.target or model.name,
        "messages": [{"role": message.role, "content": message.content} for message in request.messages],
        "stream": stream,
    }


def _extract_stream_content(data: dict[str, Any]) -> str:
    message = data.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if not isinstance(content, str):
        return ""
    return content
