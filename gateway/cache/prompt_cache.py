"""In-memory prompt response cache."""

import copy
import hashlib
import json
from collections import OrderedDict
from typing import Any

from gateway.schemas import ChatCompletionRequest


class PromptCache:
    def __init__(self, max_size: int = 1024) -> None:
        self._max_size = max_size
        self._items: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def get(self, key: str) -> dict[str, Any] | None:
        value = self._items.get(key)
        if value is None:
            return None
        self._items.move_to_end(key)
        return copy.deepcopy(value)

    def set(self, key: str, value: dict[str, Any]) -> None:
        if self._max_size <= 0:
            return
        self._items[key] = copy.deepcopy(value)
        self._items.move_to_end(key)
        while len(self._items) > self._max_size:
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()


def build_cache_key(request: ChatCompletionRequest) -> str:
    payload = {
        "model": request.model,
        "messages": [message.model_dump(mode="json") for message in request.messages],
        "temperature": request.temperature,
        "top_p": request.top_p,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
