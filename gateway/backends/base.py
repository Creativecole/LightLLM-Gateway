"""Backend interface definitions."""

from abc import ABC, abstractmethod

from gateway.config import ModelConfig
from gateway.schemas import ChatCompletionRequest, ChatCompletionResponse


class BaseBackend(ABC):
    """Base interface for chat completion backends."""

    @abstractmethod
    def chat_completion(
        self,
        request: ChatCompletionRequest,
        model: ModelConfig,
    ) -> ChatCompletionResponse:
        """Return a non-streaming chat completion response."""
