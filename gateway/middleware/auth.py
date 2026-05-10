"""API key authentication middleware."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from gateway.config import ApiKeyConfig, GatewayConfig

PUBLIC_PATHS = {"/api/health", "/api/models", "/api/requests", "/metrics"}


@dataclass(frozen=True)
class AuthenticatedUser:
    name: str
    key: str
    rpm: int


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, config: GatewayConfig) -> None:
        super().__init__(app)
        self._auth_config = config.auth
        self._api_keys = {api_key.key: api_key for api_key in self._auth_config.api_keys}

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not self._auth_config.enabled or request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        authorization = request.headers.get("Authorization")
        if authorization is None:
            return _unauthorized("Missing Authorization header")

        scheme, _, token = authorization.partition(" ")
        if scheme != "Bearer" or not token:
            return _unauthorized("Invalid Authorization header")

        api_key = self._api_keys.get(token)
        if api_key is None:
            return _unauthorized("Invalid API key")

        request.state.user = _to_user(api_key)
        return await call_next(request)


def _to_user(api_key: ApiKeyConfig) -> AuthenticatedUser:
    return AuthenticatedUser(name=api_key.name, key=api_key.key, rpm=api_key.rpm)


def _unauthorized(message: str) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": message})
