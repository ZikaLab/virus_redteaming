"""Replace the response CSV only after every selected row is ready."""

import csv
import os
from pathlib import Path

from virus_redteaming.claude_harness.models import RedTeamResult
from virus_redteaming.core.errors import VirusRedteamingError

_HEADER = (
    "ICTV virus",
    "Claude response",
    "ICTV family",
    "ICTV genus",
    "Human pathogen hazard group",
    "Schedule 5",
    "Secondary structure",
)


class RedTeamReportWriter:
    """Write the seven-column response table."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def write(self, rows: tuple[RedTeamResult, ...]) -> None:
        """Replace ``path``. A failure before the replace leaves the previous file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".csv.writing")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(_HEADER)
            for row in rows:
                writer.writerow(
                    (
                        row.virus,
                        row.claude_response,
                        row.family,
                        row.genus,
                        row.hazard_group,
                        row.schedule_5,
                        row.secondary_structure,
                    )
                )
        try:
            os.replace(temporary, self._path)
        except OSError as exc:
            raise VirusRedteamingError("output CSV cannot be replaced") from exc
