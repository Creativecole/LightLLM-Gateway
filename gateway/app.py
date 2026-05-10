"""FastAPI application factory."""

import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

from gateway.cache.prompt_cache import PromptCache, build_cache_key
from gateway.config import GatewayConfig, load_config
from gateway.logging.request_logger import RequestLogger
from gateway.middleware.auth import AuthMiddleware
from gateway.middleware.rate_limit import RateLimitMiddleware
from gateway.metrics.collector import MetricsCollector
from gateway.router.model_router import ModelRouter
from gateway.schemas import ChatCompletionRequest, ChatCompletionResponse


def create_app(config: GatewayConfig | None = None) -> FastAPI:
    app_config = config or load_config()
    app = FastAPI(title="LightLLM-Gateway")
    app.state.config = app_config
    app.state.model_router = ModelRouter(app_config)
    app.state.prompt_cache = PromptCache(max_size=app_config.cache.max_size)
    app.state.metrics = MetricsCollector()
    app.state.request_logger = RequestLogger(
        path=app_config.logging.request_log_path,
        enabled=app_config.logging.request_logs_enabled,
    )
    app.add_middleware(RateLimitMiddleware, config=app_config)
    app.add_middleware(AuthMiddleware, config=app_config)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/info")
    def info() -> dict[str, str]:
        return {"name": "LightLLM-Gateway", "version": "0.1.0"}

    @app.get("/metrics")
    async def metrics() -> dict[str, object]:
        return await app.state.metrics.snapshot()

    @app.post("/v1/chat/completions", response_model=None)
    async def chat_completions(
        http_request: Request,
        request: ChatCompletionRequest,
    ) -> dict[str, object] | ChatCompletionResponse | StreamingResponse:
        request_id = f"req-{uuid.uuid4().hex}"
        started_at = time.monotonic()
        backend = _backend_name(app.state.model_router, request.model)
        await app.state.metrics.start_request(model=request.model, backend=backend)

        if request.stream:
            stream = app.state.model_router.stream_chat_completion(request)
            return StreamingResponse(
                _instrument_stream(
                    stream=stream,
                    request_id=request_id,
                    started_at=started_at,
                    http_request=http_request,
                    chat_request=request,
                    backend=backend,
                    metrics=app.state.metrics,
                    request_logger=app.state.request_logger,
                ),
                media_type="text/event-stream",
            )

        cache_hit = False
        try:
            if not app_config.cache.enabled:
                response = await app.state.model_router.chat_completion(request)
                response_data = response.model_dump(mode="json")
                await _finish_non_streaming_request(
                    request_id=request_id,
                    started_at=started_at,
                    http_request=http_request,
                    chat_request=request,
                    backend=backend,
                    cache_hit=cache_hit,
                    status="success",
                    error=None,
                    metrics=app.state.metrics,
                    request_logger=app.state.request_logger,
                )
                return response_data

            cache_key = build_cache_key(request)
            cached_response = app.state.prompt_cache.get(cache_key)
            if cached_response is not None:
                cache_hit = True
                cached_response["cache_hit"] = True
                await _finish_non_streaming_request(
                    request_id=request_id,
                    started_at=started_at,
                    http_request=http_request,
                    chat_request=request,
                    backend=backend,
                    cache_hit=cache_hit,
                    status="success",
                    error=None,
                    metrics=app.state.metrics,
                    request_logger=app.state.request_logger,
                )
                return cached_response

            response = await app.state.model_router.chat_completion(request)
            response_data = response.model_dump(mode="json")
            response_data["cache_hit"] = False
            app.state.prompt_cache.set(cache_key, response_data)
            await _finish_non_streaming_request(
                request_id=request_id,
                started_at=started_at,
                http_request=http_request,
                chat_request=request,
                backend=backend,
                cache_hit=cache_hit,
                status="success",
                error=None,
                metrics=app.state.metrics,
                request_logger=app.state.request_logger,
            )
            return response_data
        except Exception as exc:
            await _finish_non_streaming_request(
                request_id=request_id,
                started_at=started_at,
                http_request=http_request,
                chat_request=request,
                backend=backend,
                cache_hit=cache_hit,
                status="failed",
                error=str(exc),
                metrics=app.state.metrics,
                request_logger=app.state.request_logger,
            )
            raise

    return app


def _backend_name(model_router: ModelRouter, model: str) -> str | None:
    try:
        return model_router.backend_name_for_model(model)
    except (AttributeError, HTTPException):
        return None


async def _finish_non_streaming_request(
    *,
    request_id: str,
    started_at: float,
    http_request: Request,
    chat_request: ChatCompletionRequest,
    backend: str | None,
    cache_hit: bool,
    status: str,
    error: str | None,
    metrics: MetricsCollector,
    request_logger: RequestLogger,
) -> None:
    total_latency_ms = _elapsed_ms(started_at)
    await metrics.finish_request(
        success=status == "success",
        cache_hit=cache_hit,
        latency_ms=total_latency_ms,
    )
    await request_logger.log(
        _request_log_record(
            request_id=request_id,
            http_request=http_request,
            chat_request=chat_request,
            backend=backend,
            cache_hit=cache_hit,
            ttft_ms=None,
            total_latency_ms=total_latency_ms,
            status=status,
            error=error,
        )
    )


async def _instrument_stream(
    *,
    stream: AsyncIterator[str],
    request_id: str,
    started_at: float,
    http_request: Request,
    chat_request: ChatCompletionRequest,
    backend: str | None,
    metrics: MetricsCollector,
    request_logger: RequestLogger,
) -> AsyncIterator[str]:
    status = "success"
    error: str | None = None
    ttft_ms: float | None = None
    try:
        async for chunk in stream:
            if ttft_ms is None:
                ttft_ms = _elapsed_ms(started_at)
            yield chunk
    except Exception as exc:
        status = "failed"
        error = str(exc)
        raise
    finally:
        total_latency_ms = _elapsed_ms(started_at)
        await metrics.finish_request(
            success=status == "success",
            cache_hit=False,
            latency_ms=total_latency_ms,
            ttft_ms=ttft_ms,
        )
        await request_logger.log(
            _request_log_record(
                request_id=request_id,
                http_request=http_request,
                chat_request=chat_request,
                backend=backend,
                cache_hit=False,
                ttft_ms=ttft_ms,
                total_latency_ms=total_latency_ms,
                status=status,
                error=error,
            )
        )


def _request_log_record(
    *,
    request_id: str,
    http_request: Request,
    chat_request: ChatCompletionRequest,
    backend: str | None,
    cache_hit: bool,
    ttft_ms: float | None,
    total_latency_ms: float,
    status: str,
    error: str | None,
) -> dict[str, object]:
    user = getattr(http_request.state, "user", None)
    return {
        "request_id": request_id,
        "time": datetime.now(UTC).isoformat(),
        "user": getattr(user, "name", "anonymous"),
        "model": chat_request.model,
        "backend": backend,
        "stream": chat_request.stream,
        "cache_hit": cache_hit,
        "ttft_ms": ttft_ms,
        "total_latency_ms": total_latency_ms,
        "status": status,
        "error": error,
    }


def _elapsed_ms(started_at: float) -> float:
    return (time.monotonic() - started_at) * 1000
