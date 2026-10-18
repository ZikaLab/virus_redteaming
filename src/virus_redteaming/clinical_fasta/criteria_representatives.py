"""Read chosen rows from the criteria table. The CSV module unescapes once."""

import csv
from pathlib import Path

from virus_redteaming.clinical_fasta.errors import NcbiInputError
from virus_redteaming.clinical_fasta.models import ChosenAccession

_REQUIRED = ("Query", "Accession", "Representative")


class CriteriaCsvRepresentativeSource:
    """Reads Representative 1 rows. Field text is already the original text."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self) -> tuple[ChosenAccession, ...]:
        """Return one chosen accession per trimmed query."""
        if not self._path.is_file():
            raise NcbiInputError(f"criteria file is missing: {self._path}")
        with self._path.open(encoding="utf-8", newline="") as handle:
            reader = csv.reader(
                handle,
                quoting=csv.QUOTE_NONE,
                escapechar="\\",
                doublequote=False,
            )
            try:
                header = next(reader)
            except StopIteration as exc:
                raise NcbiInputError("criteria file is empty") from exc
            indexes = _indexes(header)
            chosen: dict[str, str] = {}
            for row in reader:
                if not row or all(cell == "" for cell in row):
                    continue
                query, accession, flag = _chosen_cells(row, indexes)
                if flag != "1":
                    continue
                key = query.strip()
                if not key or not accession.strip():
                    raise NcbiInputError(
                        "chosen criteria row has a blank query or accession"
                    )
                previous = chosen.get(key)
                if previous is not None and previous != accession:
                    raise NcbiInputError(
                        "two chosen rows share a query and differ in accession"
                    )
                chosen[key] = accession
        return tuple(
            ChosenAccession(query=query, accession=accession)
            for query, accession in chosen.items()
        )


class CriteriaRepresentativeFiles:
    """Opens a criteria reader after the criteria path is known."""

    def open(self, path: Path) -> CriteriaCsvRepresentativeSource:
        """Return a reader bound to the written criteria file."""
        return CriteriaCsvRepresentativeSource(path)


def _indexes(header: list[str]) -> dict[str, int]:
    if any(name not in header for name in _REQUIRED):
        raise NcbiInputError("criteria file is missing a required header")
    return {name: header.index(name) for name in _REQUIRED}


def _chosen_cells(row: list[str], indexes: dict[str, int]) -> tuple[str, str, str]:
    try:
        query = row[indexes["Query"]]
        accession = row[indexes["Accession"]]
        flag = row[indexes["Representative"]]
    except IndexError as exc:
        raise NcbiInputError("criteria row is missing a required cell") from exc
    if flag not in {"0", "1"}:
        raise NcbiInputError("criteria Representative is not 0 or 1")
    return query, accession, flag
