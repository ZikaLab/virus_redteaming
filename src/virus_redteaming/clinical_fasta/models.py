"""Frozen values for accession hits, search misses, and FASTA text."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AccessionHit:
    """One kept search hit."""

    virus: str
    rank: int
    accession: str


@dataclass(frozen=True)
class SearchResult:
    """A published accession table and the Virus cells that returned no hits."""

    path: Path
    misses: tuple[str, ...]


@dataclass(frozen=True)
class FastaRecord:
    """FASTA text addressed by the requested accession, not the header id."""

    accession: str
    text: str
