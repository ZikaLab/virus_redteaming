"""Seams for parsing, scanning, and the local FASTA cache."""

from pathlib import Path
from typing import Protocol

from virus_redteaming.ncbi_fasta.models import GenBankTableScan


class SegmentParser(Protocol):
    """Extracts accession codes from one GenBank cell."""

    def codes(self, cell: str) -> tuple[str, ...]:
        """Return distinct codes in cell order."""


class GenBankSource(Protocol):
    """Reads the merged table."""

    def read(self) -> GenBankTableScan:
        """Return distinct codes and the blank-row count."""


class FastaCache(Protocol):
    """Looks up a FASTA file that already matches the requested accession."""

    def cached(self, accession: str) -> Path | None:
        """Return the existing file, or None when it must be fetched."""
