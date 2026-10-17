"""Turn classified table rows into VirusRecord values."""

from __future__ import annotations

from typing import Sequence

from virus_redteaming.catalogue.errors import MissingVirusSectionError
from virus_redteaming.catalogue.models import SCHEDULE_5_MARK, TableRow, VirusRecord
from virus_redteaming.catalogue.row_classifier import RowClassifier, RowKind
from virus_redteaming.catalogue.text import collapse_whitespace, row_has_schedule_5


class ApprovedVirusListParser:
    def __init__(self, classifier: RowClassifier | None = None) -> None:
        self._classifier = classifier or RowClassifier()

    def parse(self, rows: Sequence[TableRow]) -> tuple[VirusRecord, ...]:
        records: list[VirusRecord] = []
        family = ""
        genus = ""
        in_section = False
        saw_start = False
        for row in rows:
            kind = self._classifier.classify(row)
            if kind is RowKind.SECTION_END:
                break
            if kind is RowKind.SECTION_START:
                in_section = True
                saw_start = True
                continue
            if not in_section:
                continue
            if kind is RowKind.FAMILY:
                family = self._classifier.family_name(row.agent)
                genus = ""
            elif kind is RowKind.GENUS:
                genus = self._classifier.genus_name(row.agent)
            elif kind is RowKind.FAMILY_AND_GENUS:
                family = self._classifier.family_name(row.agent)
                genus = self._classifier.genus_name(row.agent)
            elif kind is RowKind.AGENT:
                records.append(
                    VirusRecord(
                        family=family,
                        genus=genus,
                        virus=collapse_whitespace(row.agent),
                        hazard_group=collapse_whitespace(row.hazard_group),
                        schedule_5=SCHEDULE_5_MARK
                        if row_has_schedule_5(row.agent, row.hazard_group, row.notes)
                        else "",
                    )
                )
        if not saw_start:
            raise MissingVirusSectionError("No 'Viruses' heading found in extracted rows.")
        return tuple(records)
