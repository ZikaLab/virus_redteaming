"""Configuration and reply errors for the Claude ping."""

import re

from virus_redteaming.core.errors import VirusRedteamingError

_SECRET = re.compile(r"sk-ant-[A-Za-z0-9_\-]+")


class MissingClaudeApiKeyError(VirusRedteamingError):
    """ANTHROPIC_API_KEY is unset or blank."""


class EmptyClaudeReplyError(VirusRedteamingError):
    """Claude returned no text."""


class ChainCountError(VirusRedteamingError):
    """The prompt list length does not match the layer's chain count."""


def redact_client_error(exc: BaseException, hidden: tuple[str, ...] = ()) -> str:
    """Remove API keys and local sequence paths from ``exc``."""
    text = _SECRET.sub("***", str(exc))
    for path in hidden:
        if path:
            text = text.replace(path, "")
    return text
