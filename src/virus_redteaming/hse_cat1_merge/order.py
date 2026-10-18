"""Sort key for the published HSE and Category 1 table."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from virus_redteaming.hse_cat1_merge.errors import MergeSortError
from virus_redteaming.hse_cat1_merge.models import MergedVirusRow

GENUS_COLUMN = "ICTV genus"
HAZARD_COLUMN = "Human pathogen hazard group"
SCHEDULE_COLUMN = "Schedule 5"
HAZARD_DESCENDING: tuple[str, ...] = ("4", "3*", "3", "2", "1")
SCHEDULE_DESCENDING: tuple[str, ...] = ("1", "0")


class MergedRowOrder(Protocol):
    def sort(self, rows: Sequence[MergedVirusRow]) -> tuple[MergedVirusRow, ...]:
        """Return every row in published order."""


class MergedTableOrder:
    """Genus A to Z, hazard group 4 to 1, Schedule 5 from 1 to 0."""

    def __init__(self) -> None:
        self._hazard = _ranks(HAZARD_DESCENDING)
        self._schedule = _ranks(SCHEDULE_DESCENDING)

    def sort_key(self, row: MergedVirusRow, position: int) -> tuple[str, int, int, int]:
        return (
            row.ictv_genus,
            _rank(self._hazard, row.hazard_group, HAZARD_COLUMN),
            _rank(self._schedule, row.schedule_5, SCHEDULE_COLUMN),
            position,
        )

    def sort(self, rows: Sequence[MergedVirusRow]) -> tuple[MergedVirusRow, ...]:
        indexed = list(enumerate(rows))
        indexed.sort(key=lambda item: self.sort_key(item[1], item[0]))
        return tuple(row for _, row in indexed)


def _ranks(values: tuple[str, ...]) -> dict[str, int]:
    return {value: index for index, value in enumerate(values)}


def _rank(ranks: dict[str, int], value: str, column: str) -> int:
    try:
        return ranks[value]
    except KeyError as exc:
        raise MergeSortError(f"{column} {value!r} is outside the sort order") from exc
