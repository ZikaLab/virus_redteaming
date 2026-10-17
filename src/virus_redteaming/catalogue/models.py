"""Value objects for the Approved List virus catalogue."""

from __future__ import annotations

from dataclasses import dataclass

CSV_COLUMNS: tuple[str, ...] = (
    "Family",
    "Genus",
    "Virus",
    "Human pathogen hazard group",
    "schedule 5",
)

SCHEDULE_5_MARK = "§"


@dataclass(frozen=True)
class TableRow:
    """One extracted table row (three source columns)."""

    agent: str
    hazard_group: str
    notes: str
    printed_page: int = 0

    def combined_text(self) -> str:
        return " ".join(part for part in (self.agent, self.hazard_group, self.notes) if part)


@dataclass(frozen=True)
class VirusRecord:
    family: str
    genus: str
    virus: str
    hazard_group: str
    schedule_5: str

    def as_csv_tuple(self) -> tuple[str, str, str, str, str]:
        return (
            self.family,
            self.genus,
            self.virus,
            self.hazard_group,
            self.schedule_5,
        )
