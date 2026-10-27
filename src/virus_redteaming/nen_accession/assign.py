"""Attach the chosen NCBI accession to each nen row."""

from __future__ import annotations

from virus_redteaming.nen_accession.models import (
    AssignmentReport,
    NenVirusRecord,
    cleaned_virus_name,
)
from virus_redteaming.nen_accession.protocols import AccessionParser, VirusIndex


class NenAccessionAssigner:
    def __init__(self, index: VirusIndex, parser: AccessionParser) -> None:
        self._index = index
        self._parser = parser

    def assign(
        self, rows: tuple[NenVirusRecord, ...]
    ) -> tuple[tuple[NenVirusRecord, ...], AssignmentReport]:
        updated: list[NenVirusRecord] = []
        unmatched: list[str] = []
        seen_unmatched: set[str] = set()
        matched = 0
        blank = 0
        for row in rows:
            name = cleaned_virus_name(row.nen_virus)
            if not name:
                blank += 1
                updated.append(row.with_ncbi(""))
                continue
            isolate = self._index.isolate(row.nen_virus)
            if isolate is None:
                if name not in seen_unmatched:
                    unmatched.append(row.nen_virus)
                    seen_unmatched.add(name)
                updated.append(row.with_ncbi(""))
                continue
            matched += 1
            updated.append(row.with_ncbi(self._parser.join(isolate.genbank_field)))
        report = AssignmentReport(
            matched=matched,
            unmatched_names=tuple(unmatched),
            blank_nen_virus=blank,
        )
        return tuple(updated), report
