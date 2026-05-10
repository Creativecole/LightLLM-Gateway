from pathlib import Path

import pytest

from gateway.config import CONFIG_ENV_VAR, load_config


CONFIG_TEXT = """
server:
  host: 127.0.0.1
  port: 8000
  reload: false

auth:
  enabled: true
  api_keys:
    - key: sk-demo
      name: demo-user
      rpm: 60

models:
  default: llama3.1
  items:
    - name: mock-small
      backend: mock
      target: mock-small
    - name: llama3.1
      backend: ollama
      target: llama3.1
      endpoint: http://127.0.0.1:11434

cache:
  enabled: true
  max_size: 1024

logging:
  request_log_path: logs/requests.jsonl
"""


def test_load_config_reads_default_config_yaml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)
    (tmp_path / "config.yaml").write_text(CONFIG_TEXT)

    config = load_config()

    assert config.models.default == "llama3.1"
    assert config.auth.api_keys[0].key == "sk-demo"


def test_load_config_reads_lightllm_config_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "custom.yaml"
    config_path.write_text(CONFIG_TEXT.replace("llama3.1", "qwen2.5"))
    monkeypatch.setenv(CONFIG_ENV_VAR, str(config_path))

    config = load_config()

    assert config.models.default == "qwen2.5"


def test_load_config_falls_back_to_config_example(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)
    (tmp_path / "config.example.yaml").write_text(CONFIG_TEXT)

    config = load_config()

    assert config.models.items[1].name == "llama3.1"
    assert config.models.items[1].target == "llama3.1"


def test_model_name_and_target_parse_independently(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        CONFIG_TEXT.replace("name: llama3.1", "name: qwen2.5").replace(
            "target: llama3.1", "target: qwen2.5:1.5b"
        )
    )

    config = load_config(config_path)
    ollama_model = config.models.items[1]

    assert ollama_model.name == "qwen2.5"
    assert ollama_model.target == "qwen2.5:1.5b"
