"""FastAPI application factory."""

from fastapi import FastAPI, HTTPException

from gateway.config import GatewayConfig, load_config
from gateway.router.model_router import ModelRouter
from gateway.schemas import ChatCompletionRequest, ChatCompletionResponse


def create_app(config: GatewayConfig | None = None) -> FastAPI:
    app_config = config or load_config()
    app = FastAPI(title="LightLLM-Gateway")
    app.state.config = app_config
    app.state.model_router = ModelRouter(app_config)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/info")
    def info() -> dict[str, str]:
        return {"name": "LightLLM-Gateway", "version": "0.1.0"}

    @app.get("/metrics")
    def metrics() -> dict[str, dict[str, object]]:
        return {"metrics": {}}

    @app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
    async def chat_completions(request: ChatCompletionRequest) -> ChatCompletionResponse:
        if request.stream:
            raise HTTPException(status_code=400, detail="stream=true is not supported yet")
        return await app.state.model_router.chat_completion(request)

    return app
