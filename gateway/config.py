"""Application configuration loading."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False


class AuthConfig(BaseModel):
    enabled: bool = False
    api_keys: list["ApiKeyConfig"] = Field(default_factory=list)


class ApiKeyConfig(BaseModel):
    key: str
    name: str
    rpm: int = 60


class ModelConfig(BaseModel):
    name: str
    backend: str
    target: str | None = None
    endpoint: str | None = None


class ModelsConfig(BaseModel):
    default: str = "mock-small"
    items: list[ModelConfig] = Field(default_factory=list)


class CacheConfig(BaseModel):
    enabled: bool = True
    ttl_seconds: int = 300
    max_size: int = 1024


class LoggingConfig(BaseModel):
    level: str = "INFO"
    request_logs_enabled: bool = True


class GatewayConfig(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def load_config(path: str | Path = "config.yaml") -> GatewayConfig:
    config_path = Path(path)
    if not config_path.exists():
        return GatewayConfig()

    raw_config: dict[str, Any] = yaml.safe_load(config_path.read_text()) or {}
    return GatewayConfig.model_validate(raw_config)
