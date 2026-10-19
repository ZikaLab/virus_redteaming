"""Configuration and reply errors for the Claude ping."""

from virus_redteaming.core.errors import VirusRedteamingError


class MissingClaudeApiKeyError(VirusRedteamingError):
    """ANTHROPIC_API_KEY is unset or blank."""


class EmptyClaudeReplyError(VirusRedteamingError):
    """Claude returned no text."""


class ChainCountError(VirusRedteamingError):
    """The prompt list length does not match the layer's chain count."""
