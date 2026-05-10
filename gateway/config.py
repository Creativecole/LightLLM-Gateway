"""Application configuration loading."""

import os
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
    max_context_tokens: int | None = None


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
    request_log_path: str = "logs/requests.jsonl"


class GatewayConfig(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


CONFIG_ENV_VAR = "LIGHTLLM_CONFIG"
DEFAULT_CONFIG_PATH = Path("config.yaml")
EXAMPLE_CONFIG_PATH = Path("config.example.yaml")


def load_config(path: str | Path | None = None) -> GatewayConfig:
    config_path = _resolve_config_path(path)
    raw_config: dict[str, Any] = yaml.safe_load(config_path.read_text()) or {}
    return GatewayConfig.model_validate(raw_config)


def _resolve_config_path(path: str | Path | None = None) -> Path:
    if path is not None:
        return _existing_path(Path(path))

    env_path = os.getenv(CONFIG_ENV_VAR)
    if env_path:
        return _existing_path(Path(env_path))

    if DEFAULT_CONFIG_PATH.exists():
        return DEFAULT_CONFIG_PATH
    if EXAMPLE_CONFIG_PATH.exists():
        return EXAMPLE_CONFIG_PATH

    raise FileNotFoundError(
        "No configuration file found. Create config.yaml, copy config.example.yaml, "
        f"or set {CONFIG_ENV_VAR}=/path/to/config.yaml."
    )


def _existing_path(path: Path) -> Path:
    if path.exists():
        return path
    raise FileNotFoundError(f"Configuration file not found: {path}")
