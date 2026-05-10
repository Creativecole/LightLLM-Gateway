"""JSONL request logger."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


class RequestLogger:
    def __init__(self, path: str, enabled: bool = True) -> None:
        self._path = Path(path)
        self._enabled = enabled

    async def log(self, record: dict[str, Any]) -> None:
        if not self._enabled:
            return
        try:
            await asyncio.to_thread(self._write, record)
        except OSError:
            LOGGER.exception("Failed to write request log")

    def _write(self, record: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False))
            log_file.write("\n")
