"""Long-format CSV writer for VirusRecord values."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence, TextIO

from virus_redteaming.catalogue.models import CSV_COLUMNS, VirusRecord


class LongFormatCsvWriter:
    def __init__(self, destination: Path) -> None:
        self._destination = destination

    def write(self, records: Sequence[VirusRecord]) -> None:
        self._destination.parent.mkdir(parents=True, exist_ok=True)
        with self._destination.open("w", encoding="utf-8", newline="") as handle:
            self.write_to(handle, records)

    def write_to(self, handle: TextIO, records: Sequence[VirusRecord]) -> None:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(CSV_COLUMNS)
        for record in records:
            writer.writerow(record.as_csv_tuple())
