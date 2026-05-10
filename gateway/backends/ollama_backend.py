"""Ollama backend adapter for non-streaming chat completions."""

import time
import uuid
from typing import Any

import httpx
from fastapi import HTTPException

from gateway.backends.base import BaseBackend
from gateway.config import ModelConfig
from gateway.schemas import ChatCompletionChoice, ChatCompletionRequest, ChatCompletionResponse, Usage

DEFAULT_OLLAMA_ENDPOINT = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT_SECONDS = 30.0


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


def _extract_message(data: dict[str, Any]) -> dict[str, str]:
    message = data.get("message")
    if not isinstance(message, dict):
        raise HTTPException(status_code=502, detail="Ollama response missing message")

    role = message.get("role") or "assistant"
    content = message.get("content")
    if not isinstance(content, str):
        raise HTTPException(status_code=502, detail="Ollama response missing message content")

    return {"role": role, "content": content}
