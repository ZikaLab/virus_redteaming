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
class MeasuredFasta:
    """One local FASTA header and the sequence after it."""

    header: str
    header_words: tuple[str, ...]
    gene_length: int
    sequence: str


@dataclass(frozen=True)
class CriteriaRow:
    """One scored accession. Query and sequence are the original text."""

    query: str
    rank: int
    accession: str
    screened_words: tuple[str, ...]
    in_order: bool
    adjacent: bool
    word_match_count: int
    matched_words: tuple[str, ...]
    match_continuation_penalty: int | None
    gene_length: int | None
    within_cutoff: bool
    header: str
    failure: str
    representative: bool
    sequence: str


@dataclass(frozen=True)
class ChosenAccession:
    """A representative accession whose query has had end spaces removed."""

    query: str
    accession: str


@dataclass(frozen=True)
class FastaRecord:
    """FASTA text addressed by the requested accession, not the header id."""

    accession: str
    text: str
