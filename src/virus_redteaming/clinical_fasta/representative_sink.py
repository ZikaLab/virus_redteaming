"""Write chosen sequences with ordinary CSV quoting."""

import csv
from pathlib import Path
from typing import IO

from virus_redteaming.clinical_fasta.atomic_replace import replace_text
from virus_redteaming.clinical_fasta.models import CriteriaRow

_HEADER = ("Query", "Accession", "GeneLength", "Sequence", "Representative")


class AtomicRepresentativeSink:
    """Replaces NCBI_representative_seq.csv only after the temp file is complete."""

    def __init__(self, destination: Path) -> None:
        self._destination = destination

    def write(self, rows: tuple[CriteriaRow, ...] | list[CriteriaRow]) -> Path:
        """Write one row per chosen group and return the destination path."""

        def write_rows(handle: IO[str]) -> None:
            writer = csv.writer(handle)
            writer.writerow(_HEADER)
            for row in rows:
                if row.representative:
                    writer.writerow(
                        [
                            row.query,
                            row.accession,
                            "" if row.gene_length is None else str(row.gene_length),
                            row.sequence,
                            "1",
                        ]
                    )

        return replace_text(self._destination, write_rows)
