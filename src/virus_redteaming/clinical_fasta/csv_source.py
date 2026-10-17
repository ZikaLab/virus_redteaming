"""Read the Virus column from a query CSV."""

import csv
from pathlib import Path

from virus_redteaming.clinical_fasta.errors import NcbiInputError


class OutputCsvVirusSource:
    """Yields trimmed Virus cells and skips blanks."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self) -> tuple[str, ...]:
        """Return non-blank Virus cells in file order."""
        if not self._path.is_file():
            raise NcbiInputError(f"query CSV is missing: {self._path}")
        with self._path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or "Virus" not in reader.fieldnames:
                raise NcbiInputError("query CSV is missing a Virus header")
            cells = tuple(
                (row.get("Virus") or "").strip()
                for row in reader
                if (row.get("Virus") or "").strip()
            )
        if not cells:
            raise NcbiInputError("query CSV has no non-blank Virus cells")
        return cells
