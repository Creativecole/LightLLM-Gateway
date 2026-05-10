"""Server-Sent Events formatting helpers."""

import json
from typing import Any


def format_sse_data(payload: dict[str, Any] | str) -> str:
    if isinstance(payload, str):
        data = payload
    else:
        data = json.dumps(payload, separators=(",", ":"))
    return f"data: {data}\n\n"


def format_chat_delta(content: str) -> str:
    return format_sse_data({"choices": [{"delta": {"content": content}}]})


def format_error(message: str) -> str:
    return format_sse_data({"error": {"message": message}})


def format_done() -> str:
    return format_sse_data("[DONE]")
