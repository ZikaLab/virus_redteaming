"""Biopython Entrez adapter. Sockets live only in this module."""

from typing import Any

from Bio import Entrez

from virus_redteaming.clinical_fasta.config import NcbiEntrezConfig
from virus_redteaming.clinical_fasta.errors import NcbiFetchError


class BiopythonEntrezClient:
    """esearch for part 1 and efetch FASTA text for part 2."""

    def __init__(self, config: NcbiEntrezConfig) -> None:
        self._config = config

    def search(self, term: str) -> tuple[str, ...]:
        """Return IdList in NCBI order. Does not call efetch."""
        self._apply_config()
        handle = Entrez.esearch(**self._search_arguments(term))  # type: ignore[no-untyped-call]
        try:
            payload: Any = Entrez.read(handle)  # type: ignore[no-untyped-call]
        except Exception as exc:
            raise NcbiFetchError("esearch body could not be read") from exc
        finally:
            handle.close()
        id_list = payload.get("IdList", [])
        return tuple(id_list)

    def fetch_fasta(self, accession: str) -> str:
        """Read one FASTA body, close the handle, and return the text."""
        self._apply_config()
        handle = Entrez.efetch(**self._fetch_arguments(accession))  # type: ignore[no-untyped-call]
        try:
            text = handle.read()
        except Exception as exc:
            raise NcbiFetchError("efetch body could not be read") from exc
        finally:
            handle.close()
        if isinstance(text, bytes):
            return text.decode("utf-8")
        return str(text)

    def _apply_config(self) -> None:
        Entrez.email = self._config.email  # type: ignore[assignment]
        Entrez.tool = self._config.tool
        Entrez.api_key = self._config.api_key  # type: ignore[assignment]

    def _search_arguments(self, term: str) -> dict[str, object]:
        arguments: dict[str, object] = {
            "db": "nuccore",
            "term": term,
            "retmax": 5,
            "retstart": 0,
            "idtype": "acc",
            "tool": self._config.tool,
            "email": self._config.email,
        }
        if self._config.api_key is not None:
            arguments["api_key"] = self._config.api_key
        return arguments

    def _fetch_arguments(self, accession: str) -> dict[str, object]:
        arguments: dict[str, object] = {
            "db": "nuccore",
            "id": accession,
            "rettype": "fasta",
            "retmode": "text",
            "tool": self._config.tool,
            "email": self._config.email,
        }
        if self._config.api_key is not None:
            arguments["api_key"] = self._config.api_key
        return arguments
