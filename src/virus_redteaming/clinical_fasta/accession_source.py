"""Read distinct accessions. The CLI passes output/accessions.csv."""

import csv
import re
from pathlib import Path

from virus_redteaming.clinical_fasta.errors import NcbiInputError

_ACCESSION = re.compile(r"^[A-Z]{1,6}_?[0-9]+(\.[0-9]+)?$")


class AccessionCsvSource:
    """Validates accession syntax and drops repeats."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self) -> tuple[str, ...]:
        """Return distinct accessions in first-seen order."""
        if not self._path.is_file():
            raise NcbiInputError(f"accession file is missing: {self._path}")
        with self._path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or "Accession" not in reader.fieldnames:
                raise NcbiInputError("accession file is missing an Accession header")
            seen: list[str] = []
            for row in reader:
                accession = (row.get("Accession") or "").strip()
                if not accession:
                    continue
                if _ACCESSION.fullmatch(accession) is None:
                    raise NcbiInputError(f"accession is malformed: {accession}")
                if accession not in seen:
                    seen.append(accession)
        if not seen:
            raise NcbiInputError("accession file has no data rows")
        return tuple(seen)
