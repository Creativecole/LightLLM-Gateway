"""Deterministic mock backend."""

import time
import uuid
from collections.abc import AsyncIterator

from gateway.backends.base import BaseBackend
from gateway.config import ModelConfig
from gateway.schemas import ChatCompletionChoice, ChatCompletionRequest, ChatCompletionResponse, Usage
from gateway.sse import format_chat_delta, format_done


class MockBackend(BaseBackend):
    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        model: ModelConfig,
    ) -> ChatCompletionResponse:
        content = "Hello from MockBackend"
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message={"role": "assistant", "content": content},
                    finish_reason="stop",
                )
            ],
            usage=Usage(
                prompt_tokens=_count_message_tokens(request),
                completion_tokens=len(content.split()),
                total_tokens=_count_message_tokens(request) + len(content.split()),
            ),
        )

    async def stream_chat_completion(
        self,
        request: ChatCompletionRequest,
        model: ModelConfig,
    ) -> AsyncIterator[str]:
        yield format_chat_delta("Hello from MockBackend")
        yield format_done()


def _count_message_tokens(request: ChatCompletionRequest) -> int:
    return sum(len(message.content.split()) for message in request.messages)
