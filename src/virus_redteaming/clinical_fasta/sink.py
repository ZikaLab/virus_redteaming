"""Atomically write one FASTA file. The CLI passes output/clinical_genes."""

import os
import tempfile
from pathlib import Path

from virus_redteaming.clinical_fasta.errors import FastaWriteError
from virus_redteaming.clinical_fasta.models import FastaRecord


class AtomicPathFastaSink:
    """Replaces ``{directory}/{accession}.fasta``."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def write(self, record: FastaRecord) -> Path:
        """Write one FASTA file and return its path."""
        self._directory.mkdir(parents=True, exist_ok=True)
        destination = self._directory / f"{record.accession}.fasta"
        handle = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self._directory,
            prefix=f".{record.accession}.",
            suffix=".tmp",
            delete=False,
        )
        temporary = Path(handle.name)
        try:
            handle.write(record.text)
            handle.flush()
            handle.close()
            os.replace(temporary, destination)
        except Exception as exc:
            handle.close()
            temporary.unlink(missing_ok=True)
            raise FastaWriteError("FASTA file was not replaced") from exc
        return destination
