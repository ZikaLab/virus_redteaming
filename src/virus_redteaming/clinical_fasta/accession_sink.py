"""Atomically write the accession table. The CLI passes output/accessions.csv."""

import csv
import os
import tempfile
from pathlib import Path

from virus_redteaming.clinical_fasta.errors import FastaWriteError
from virus_redteaming.clinical_fasta.models import AccessionHit


class AtomicAccessionTableSink:
    """Replaces the destination only after the temp file is complete."""

    def __init__(self, destination: Path) -> None:
        self._destination = destination

    def write(self, hits: tuple[AccessionHit, ...] | list[AccessionHit]) -> Path:
        """Write Virus, Rank, Accession and return the destination path."""
        self._destination.parent.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=self._destination.parent,
            prefix=f".{self._destination.name}.",
            suffix=".tmp",
            delete=False,
        )
        temporary = Path(handle.name)
        try:
            writer = csv.writer(handle)
            writer.writerow(["Virus", "Rank", "Accession"])
            for hit in hits:
                writer.writerow([hit.virus, hit.rank, hit.accession])
            handle.flush()
            handle.close()
            os.replace(temporary, self._destination)
        except Exception as exc:
            handle.close()
            temporary.unlink(missing_ok=True)
            raise FastaWriteError("accession table was not replaced") from exc
        return self._destination
