"""Anthropic messages client behind ``ChatTurn``."""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage
from pydantic import SecretStr

from virus_redteaming.claude_harness.config import ClaudeApiConfig

_BETA = "files-api-2025-04-14"


class AnthropicChat:
    """Send one prompt to Claude and return the text blocks."""

    def __init__(
        self,
        config: ClaudeApiConfig,
        *,
        timeout: float | None = None,
        max_tokens: int = 256,
    ) -> None:
        headers: dict[str, str] | None = None
        if config.workspace_id:
            headers = {"anthropic-workspace-id": config.workspace_id}
        self._model = ChatAnthropic(
            model_name=config.model,
            api_key=SecretStr(config.api_key),
            max_tokens_to_sample=max_tokens,
            timeout=timeout,
            stop=None,
            default_headers=headers,
        )

    def complete(self, prompt: str, file_id: str | None = None) -> str:
        """Return concatenated text from the Claude reply."""
        if file_id is None:
            message = self._model.invoke(prompt)
        else:
            message = self._model.invoke(
                [
                    HumanMessage(
                        content=[
                            {"type": "text", "text": prompt},
                            {
                                "type": "document",
                                "source": {"type": "file", "file_id": file_id},
                            },
                        ]
                    )
                ],
                betas=[_BETA],
            )
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
