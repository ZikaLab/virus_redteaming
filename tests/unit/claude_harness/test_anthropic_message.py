"""A document message is one human message, not a list of messages."""

from typing import Any

import pytest

pytest.importorskip("langchain_anthropic")

from langchain_core.messages import HumanMessage

from virus_redteaming.claude_harness.anthropic_chat import AnthropicChat
from virus_redteaming.claude_harness.config import ClaudeApiConfig


def test_file_message_is_one_human_message() -> None:
    seen: list[object] = []

    class _Reply:
        content = "10"

    class _Model:
        def invoke(self, message: object, **kwargs: Any) -> _Reply:
            seen.append(message)
            seen.append(kwargs)
            return _Reply()

    chat = AnthropicChat(
        ClaudeApiConfig(api_key="sk-ant-test"),
        timeout=180.0,
        max_tokens=4096,
    )
    chat._model = _Model()  # type: ignore[assignment]
    assert chat.complete("\r\r\rCount", file_id="file_1") == "10"
    messages = seen[0]
    assert isinstance(messages, list)
    assert len(messages) == 1
    message = messages[0]
    assert isinstance(message, HumanMessage)
    content = message.content
    assert isinstance(content, list)
    block = content[1]
    assert isinstance(block, dict)
    assert block["source"]["file_id"] == "file_1"
    assert seen[1] == {"betas": ["files-api-2025-04-14"]}
