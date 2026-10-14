"""Small shared Protocols (Interface Segregation + Dependency Inversion)."""

from typing import Protocol


class TextSource(Protocol):
    def read(self) -> str:
        """Return the next unit of text to evaluate."""


class ResultSink(Protocol):
    def write(self, payload: str) -> None:
        """Persist or emit a result payload."""
