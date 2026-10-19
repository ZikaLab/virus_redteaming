"""Read distinct GenBank accessions from the merged table."""

from __future__ import annotations

import csv
from pathlib import Path

from virus_redteaming.ncbi_fasta.errors import NcbiFastaInputError
from virus_redteaming.ncbi_fasta.models import GenBankTableScan
from virus_redteaming.ncbi_fasta.protocols import SegmentParser

_COLUMN = "GenBank accessions"


class MergedGenBankSource:
    """Skips blank cells and keeps each accession once, in first-seen order."""

    def __init__(self, path: Path, parser: SegmentParser) -> None:
        self._path = path
        self._parser = parser

    def read(self) -> GenBankTableScan:
        """Return the scan of ``path``."""
        if not self._path.is_file():
            raise NcbiFastaInputError("merged table is missing")
        seen: list[str] = []
        blank_rows = 0
        with self._path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or _COLUMN not in reader.fieldnames:
                raise NcbiFastaInputError("GenBank accessions header is missing")
            for record in reader:
                cell = (record.get(_COLUMN) or "").replace("\xa0", " ").strip()
                if not cell:
                    blank_rows += 1
                    continue
                for code in self._parser.codes(cell):
                    if code not in seen:
                        seen.append(code)
        return GenBankTableScan(tuple(seen), blank_rows)
