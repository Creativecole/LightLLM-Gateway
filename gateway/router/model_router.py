"""Model-to-backend routing."""

from fastapi import HTTPException

from gateway.backends.base import BaseBackend
from gateway.backends.mock_backend import MockBackend
from gateway.config import GatewayConfig, ModelConfig
from gateway.schemas import ChatCompletionRequest, ChatCompletionResponse


class ModelRouter:
    def __init__(self, config: GatewayConfig) -> None:
        self._models_by_name = {model.name: model for model in config.models.items}
        self._backends: dict[str, BaseBackend] = {
            "mock": MockBackend(),
        }

    def chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        model = self._find_model(request.model)
        backend = self._find_backend(model)
        return backend.chat_completion(request, model)

    def _find_model(self, model_name: str) -> ModelConfig:
        model = self._models_by_name.get(model_name)
        if model is None:
            raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")
        return model

    def _find_backend(self, model: ModelConfig) -> BaseBackend:
        backend = self._backends.get(model.backend)
        if backend is None:
            raise HTTPException(status_code=400, detail=f"Unsupported backend: {model.backend}")
        return backend
