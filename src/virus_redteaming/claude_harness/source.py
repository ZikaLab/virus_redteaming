"""Read the merged table into one row per virus that has an identity or an accession."""

import csv
from collections.abc import Mapping
from pathlib import Path

from virus_redteaming.claude_harness.models import RedTeamRow
from virus_redteaming.core.errors import VirusRedteamingError

_COLUMNS = (
    "ICTV virus",
    "NCBI accession",
    "ICTV family",
    "ICTV genus",
    "Human pathogen hazard group",
    "Schedule 5",
)


class MergedRedTeamSource:
    """Skip a row whose key and accession are both blank."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self) -> tuple[RedTeamRow, ...]:
        """Return the rows that produce an output line, in table order."""
        if not self._path.is_file():
            raise VirusRedteamingError("merged table is missing")
        rows: list[RedTeamRow] = []
        with self._path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames
            missing = fieldnames is None or any(
                column not in fieldnames for column in _COLUMNS
            )
            if missing:
                raise VirusRedteamingError("merged table is missing a column")
            for record in reader:
                virus = _cell(record, "ICTV virus")
                accession = _first_code(_cell(record, "NCBI accession"))
                if virus == "" and accession == "":
                    continue
                rows.append(
                    RedTeamRow(
                        virus=virus,
                        family=_cell(record, "ICTV family"),
                        genus=_cell(record, "ICTV genus"),
                        hazard_group=_cell(record, "Human pathogen hazard group"),
                        schedule_5=_cell(record, "Schedule 5"),
                        accession=accession,
                    )
                )
        return tuple(rows)


def _cell(record: Mapping[str, str | None], name: str) -> str:
    raw = record.get(name) or ""
    return raw.replace("\xa0", " ").strip()


def _first_code(cell: str) -> str:
    if cell == "":
        return ""
    if ";" in cell:
        return cell.split(";", 1)[0].strip()
    return cell
