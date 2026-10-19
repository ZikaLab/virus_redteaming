"""Frozen values for a scanned table and a finished download."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GenBankTableScan:
    """Distinct accessions in first-seen order, plus the blank-row count."""

    codes: tuple[str, ...]
    blank_rows: int


@dataclass(frozen=True)
class FetchNcbiFastaReport:
    """Paths written in this run, paths already cached, and blank rows."""

    written: tuple[Path, ...]
    cached: tuple[Path, ...]
    blank_rows: int
