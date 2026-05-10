"""In-memory sliding window rate limiter."""

import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from gateway.config import GatewayConfig
from gateway.middleware.auth import PUBLIC_PATHS

WINDOW_SECONDS = 60.0


class SlidingWindowRateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._requests_by_key: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, rpm: int) -> bool:
        now = self._clock()
        window_start = now - WINDOW_SECONDS
        request_times = self._requests_by_key[key]

        while request_times and request_times[0] <= window_start:
            request_times.popleft()

        if len(request_times) >= rpm:
            return False

        request_times.append(now)
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: object,
        config: GatewayConfig,
        limiter: SlidingWindowRateLimiter | None = None,
    ) -> None:
        super().__init__(app)
        self._auth_enabled = config.auth.enabled
        self._limiter = limiter or SlidingWindowRateLimiter()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not self._auth_enabled or request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        user = getattr(request.state, "user", None)
        if user is None:
            return await call_next(request)

        if not self._limiter.allow(user.key, user.rpm):
            return JSONResponse(
                status_code=429,
                content={"detail": "rate limit exceeded"},
            )

        return await call_next(request)
