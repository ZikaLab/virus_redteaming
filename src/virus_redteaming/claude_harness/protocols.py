"""Seam between the graph and a chat client."""

from typing import Protocol


class ChatTurn(Protocol):
    """One user prompt in, one text reply out."""

    def complete(self, prompt: str, file_id: str | None = None) -> str:
        """Return the model's text for ``prompt``.

        ``file_id`` is set when the prompt is sent beside an uploaded file.
        """
        ...


class SequenceStore(Protocol):
    """Upload one local sequence and delete the remote file."""

    def upload(self, accession: str) -> str:
        """Post ``{accession}.tmp`` and return its ``file_id``."""
        ...

    def delete(self, file_id: str) -> None:
        """Remove the remote file. A failure is the caller's to ignore."""
        ...
