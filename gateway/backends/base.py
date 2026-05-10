"""Backend interface definitions."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from gateway.config import ModelConfig
from gateway.schemas import ChatCompletionRequest, ChatCompletionResponse


class BaseBackend(ABC):
    """Base interface for chat completion backends."""

    @abstractmethod
    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        model: ModelConfig,
    ) -> ChatCompletionResponse:
        """Return a non-streaming chat completion response."""

    @abstractmethod
    def stream_chat_completion(
        self,
        request: ChatCompletionRequest,
        model: ModelConfig,
    ) -> AsyncIterator[str]:
        """Return streaming chat completion SSE chunks."""
