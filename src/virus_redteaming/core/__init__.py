"""Shared contracts, errors, and value objects."""

from virus_redteaming.core.errors import VirusRedteamingError
from virus_redteaming.core.protocols import ResultSink, TextSource

__all__ = ["ResultSink", "TextSource", "VirusRedteamingError"]
