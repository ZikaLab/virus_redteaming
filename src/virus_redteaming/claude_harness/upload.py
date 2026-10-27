"""Post a prepared sequence to the Files API and delete it after the chain."""

from pathlib import Path
from typing import Any, Protocol

from virus_redteaming.claude_harness.config import ClaudeApiConfig
from virus_redteaming.claude_harness.sequence import prepared_name
from virus_redteaming.core.errors import VirusRedteamingError

_BETA = "files-api-2025-04-14"


class FilePoster(Protocol):
    """The Files API calls ``SequenceUpload`` needs."""

    def post(self, *, filename: str, body: bytes, content_type: str) -> str:
        """Return the uploaded ``file_id``."""
        ...

    def remove(self, file_id: str) -> None:
        """Delete that remote file."""
        ...


class AnthropicFilePoster:
    """Live Files API client."""

    def __init__(self, config: ClaudeApiConfig) -> None:
        self._config = config
        self._client: Any = None

    def _sdk(self) -> Any:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self._config.api_key)
        return self._client

    def post(self, *, filename: str, body: bytes, content_type: str) -> str:
        """Upload ``body`` as ``filename`` and return ``file_id``."""
        client = self._sdk()
        workspace = self._config.workspace_id
        uploaded = client.beta.files.upload(
            file=(filename, body, content_type),
            expires_in_seconds=3600,
            betas=[_BETA],
            **({"workspace_id": workspace} if workspace else {}),
        )
        file_id = uploaded.id
        if not isinstance(file_id, str) or not file_id:
            raise VirusRedteamingError("file upload did not return an id")
        return file_id

    def remove(self, file_id: str) -> None:
        """Delete ``file_id``."""
        client = self._sdk()
        workspace = self._config.workspace_id
        client.beta.files.delete(
            file_id,
            betas=[_BETA],
            **({"workspace_id": workspace} if workspace else {}),
        )


class SequenceUpload:
    """Read the prepared sequence and post it as ``sequence.txt``."""

    def __init__(
        self,
        config: ClaudeApiConfig,
        directory: Path,
        poster: FilePoster | None = None,
    ) -> None:
        self._directory = directory
        self._poster = poster if poster is not None else AnthropicFilePoster(config)

    def upload(self, accession: str) -> str:
        """Post the prepared sequence file and return its ``file_id``."""
        body = (self._directory / prepared_name(accession)).read_bytes()
        return self._poster.post(
            filename="sequence.txt",
            body=body,
            content_type="text/plain",
        )

    def delete(self, file_id: str) -> None:
        """Delete the remote file."""
        self._poster.remove(file_id)
