"""Write the criteria table. The CSV module escapes commas once."""

import csv
from pathlib import Path
from typing import IO

from virus_redteaming.clinical_fasta.atomic_replace import replace_text
from virus_redteaming.clinical_fasta.models import CriteriaRow
from virus_redteaming.clinical_fasta.representative_selection import UPPER_BP

_HEADER = (
    "Query",
    "Rank",
    "Accession",
    "ScreenedWords",
    "InOrderMatch",
    "AdjacentMatch",
    "WordMatchCount",
    "MatchedWords",
    "MatchContinuationPenalty",
    "GeneLength",
    "WithinUpperCutoff",
    "Header",
    "Failure",
    "Representative",
)


class AtomicCriteriaSink:
    """Replaces accession_criteria.csv only after the temp file is complete."""

    def __init__(self, destination: Path) -> None:
        self._destination = destination

    def write(self, rows: tuple[CriteriaRow, ...] | list[CriteriaRow]) -> Path:
        """Write original field text and return the destination path."""

        def write_rows(handle: IO[str]) -> None:
            writer = csv.writer(
                handle,
                quoting=csv.QUOTE_NONE,
                escapechar="\\",
                doublequote=False,
            )
            writer.writerow(_HEADER)
            for row in rows:
                writer.writerow(_fields(row))

        return replace_text(self._destination, write_rows)


def _fields(row: CriteriaRow) -> list[str]:
    length = "" if row.gene_length is None else str(row.gene_length)
    within = "1" if row.gene_length is not None and row.gene_length <= UPPER_BP else "0"
    return [
        row.query,
        str(row.rank),
        row.accession,
        ";".join(row.screened_words),
        _flag(row.in_order),
        _flag(row.adjacent),
        str(row.word_match_count),
        ";".join(row.matched_words),
        ""
        if row.match_continuation_penalty is None
        else str(row.match_continuation_penalty),
        length,
        within,
        row.header,
        row.failure,
        _flag(row.representative),
    ]


def _flag(value: bool) -> str:
    return "1" if value else "0"
