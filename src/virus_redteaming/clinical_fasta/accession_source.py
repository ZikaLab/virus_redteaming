"""Read distinct accessions. The CLI passes output/accessions.csv."""

import csv
import re
from pathlib import Path

from virus_redteaming.clinical_fasta.errors import NcbiInputError
from virus_redteaming.clinical_fasta.models import AccessionHit

_ACCESSION = re.compile(r"^[A-Z]{1,6}_?[0-9]+(\.[0-9]+)?$")


class AccessionHitCsvSource:
    """Reads every Virus, Rank, and Accession row. Download uses the other source."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self) -> tuple[AccessionHit, ...]:
        """Return every data row in file order."""
        if not self._path.is_file():
            raise NcbiInputError(f"accession file is missing: {self._path}")
        with self._path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            names = reader.fieldnames
            if names is None or any(
                column not in names for column in ("Virus", "Rank", "Accession")
            ):
                raise NcbiInputError("accession file is missing a required header")
            hits: list[AccessionHit] = []
            for row in reader:
                hits.append(_hit(row))
        if not hits:
            raise NcbiInputError("accession file has no data rows")
        _reject_bad_groups(hits)
        return tuple(hits)


def _hit(row: dict[str, str | None]) -> AccessionHit:
    virus = row.get("Virus") or ""
    accession = (row.get("Accession") or "").strip()
    if not virus.strip() or not accession:
        raise NcbiInputError("accession row has a blank Virus or Accession cell")
    if _ACCESSION.fullmatch(accession) is None:
        raise NcbiInputError(f"accession is malformed: {accession}")
    try:
        rank = int((row.get("Rank") or "").strip())
    except ValueError as exc:
        raise NcbiInputError("accession rank is not an integer") from exc
    if rank < 1 or rank > 5:
        raise NcbiInputError("accession rank is outside 1 through 5")
    return AccessionHit(virus=virus, rank=rank, accession=accession)


def _reject_bad_groups(hits: tuple[AccessionHit, ...] | list[AccessionHit]) -> None:
    ranks: dict[str, list[int]] = {}
    for hit in hits:
        ranks.setdefault(hit.virus, []).append(hit.rank)
    for group in ranks.values():
        if len(group) > 5 or len(group) != len(set(group)):
            raise NcbiInputError("accession group is larger than 5 or repeats a rank")


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
