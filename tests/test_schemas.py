import pytest
from pydantic import ValidationError

from gateway.schemas import ChatCompletionRequest


def test_chat_completion_request_requires_messages() -> None:
    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate({"model": "mock-small", "messages": []})


def test_chat_completion_request_rejects_unknown_role() -> None:
    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate(
            {
                "model": "mock-small",
                "messages": [{"role": "invalid", "content": "Hello"}],
            }
        )
