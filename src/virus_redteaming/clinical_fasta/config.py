"""Email and API key for Entrez. The key is redacted from representations."""

import os
from dataclasses import dataclass

from virus_redteaming.clinical_fasta.errors import NcbiConfigError

_TOOL = "virus_redteaming_clinical_fasta"


@dataclass(frozen=True)
class NcbiEntrezConfig:
    """Entrez identity. ``api_key`` is omitted from the call when absent."""

    email: str
    tool: str = _TOOL
    api_key: str | None = None

    def __post_init__(self) -> None:
        if not self.email or any(character.isspace() for character in self.email):
            raise NcbiConfigError("NCBI_EMAIL is missing or contains whitespace")

    def __repr__(self) -> str:
        return (
            f"NcbiEntrezConfig(email={self.email!r}, tool={self.tool!r}, api_key='***')"
        )

    @classmethod
    def from_environment(cls) -> "NcbiEntrezConfig":
        """Read NCBI_EMAIL and the optional NCBI_API_KEY."""
        email = os.environ.get("NCBI_EMAIL", "")
        raw_key = os.environ.get("NCBI_API_KEY", "")
        api_key = raw_key if raw_key else None
        return cls(email=email, api_key=api_key)
