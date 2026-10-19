"""Anthropic messages client behind ``ChatTurn``."""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage
from pydantic import SecretStr

from virus_redteaming.claude_harness.config import ClaudeApiConfig


class AnthropicChat:
    """Send one prompt to Claude and return the text blocks."""

    def __init__(self, config: ClaudeApiConfig) -> None:
        headers: dict[str, str] | None = None
        if config.workspace_id:
            headers = {"anthropic-workspace-id": config.workspace_id}
        self._model = ChatAnthropic(
            model_name=config.model,
            api_key=SecretStr(config.api_key),
            max_tokens_to_sample=256,
            timeout=None,
            stop=None,
            default_headers=headers,
        )

    def complete(self, prompt: str) -> str:
        """Return concatenated text from the Claude reply."""
        message = self._model.invoke(prompt)
        return _message_text(message)


def _message_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    return "".join(_block_text(block) for block in content)


def _block_text(block: object) -> str:
    if isinstance(block, str):
        return block
    text = getattr(block, "text", None)
    if isinstance(text, str):
        return text
    if isinstance(block, dict):
        value = block.get("text", "")
        if isinstance(value, str) and block.get("type") == "text":
            return value
    return ""
