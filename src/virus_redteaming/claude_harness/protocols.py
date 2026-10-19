"""Seam between the graph and a chat client."""

from typing import Protocol


class ChatTurn(Protocol):
    """One user prompt in, one text reply out."""

    def complete(self, prompt: str) -> str:
        """Return the model's text for ``prompt``."""
        ...
