"""Rows that stay inside the process and the CSV result."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RedTeamRow:
    """Identity copied from one merged row, plus the one accession to send."""

    virus: str
    family: str
    genus: str
    hazard_group: str
    schedule_5: str
    accession: str


@dataclass(frozen=True)
class RedTeamResult:
    """One output row. The accession is not a column."""

    virus: str
    claude_response: str
    family: str
    genus: str
    hazard_group: str
    schedule_5: str
    secondary_structure: str
