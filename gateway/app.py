"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from gateway.cache.prompt_cache import PromptCache, build_cache_key
from gateway.config import GatewayConfig, load_config
from gateway.middleware.auth import AuthMiddleware
from gateway.middleware.rate_limit import RateLimitMiddleware
from gateway.router.model_router import ModelRouter
from gateway.schemas import ChatCompletionRequest, ChatCompletionResponse


def create_app(config: GatewayConfig | None = None) -> FastAPI:
    app_config = config or load_config()
    app = FastAPI(title="LightLLM-Gateway")
    app.state.config = app_config
    app.state.model_router = ModelRouter(app_config)
    app.state.prompt_cache = PromptCache(max_size=app_config.cache.max_size)
    app.add_middleware(RateLimitMiddleware, config=app_config)
    app.add_middleware(AuthMiddleware, config=app_config)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/info")
    def info() -> dict[str, str]:
        return {"name": "LightLLM-Gateway", "version": "0.1.0"}

    @app.get("/metrics")
    def metrics() -> dict[str, dict[str, object]]:
        return {"metrics": {}}

    @app.post("/v1/chat/completions", response_model=None)
    async def chat_completions(
        request: ChatCompletionRequest,
    ) -> dict[str, object] | ChatCompletionResponse | StreamingResponse:
        if request.stream:
            return StreamingResponse(
                app.state.model_router.stream_chat_completion(request),
                media_type="text/event-stream",
            )

        if not app_config.cache.enabled:
            return await app.state.model_router.chat_completion(request)

        cache_key = build_cache_key(request)
        cached_response = app.state.prompt_cache.get(cache_key)
        if cached_response is not None:
            cached_response["cache_hit"] = True
            return cached_response

        response = await app.state.model_router.chat_completion(request)
        response_data = response.model_dump(mode="json")
        response_data["cache_hit"] = False
        app.state.prompt_cache.set(cache_key, response_data)
        return response_data

    return app
