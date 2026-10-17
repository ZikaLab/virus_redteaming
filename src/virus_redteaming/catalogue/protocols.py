"""Seams for PDF IO and CSV output (ISP + DIP)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence

from virus_redteaming.catalogue.models import TableRow, VirusRecord


class TableExtractor(Protocol):
    def extract(self, pdf_path: Path) -> Sequence[TableRow]:
        """Return table rows from the virus section pages."""


class RecordSink(Protocol):
    def write(self, records: Sequence[VirusRecord]) -> None:
        """Persist long-format virus records."""
