"""Part 2. A short record is skipped. A run that keeps nothing fails."""

from pathlib import Path

from virus_redteaming.clinical_fasta.errors import NcbiRecordRejected
from virus_redteaming.clinical_fasta.length import LengthCutoff
from virus_redteaming.clinical_fasta.protocols import (
    AccessionTableSource,
    FastaEncoder,
    FastaRecordSource,
    FastaSink,
)


class ClinicalFastaDownload:
    """Sequences part 2. The docstring names the cutoff in ``length.py``.

    Change ``LengthCutoff.DEFAULT_BP`` in ``length.py`` when the default cutoff
    changes. ``download --min-length`` overrides that default for one run.
    ``LengthCutoff.MAX_SLEN`` is the search upper bound in the same module.
    """

    def __init__(
        self,
        accessions: AccessionTableSource,
        source: FastaRecordSource,
        cutoff: LengthCutoff,
        encoder: FastaEncoder,
        sink: FastaSink,
    ) -> None:
        self._accessions = accessions
        self._source = source
        self._cutoff = cutoff
        self._encoder = encoder
        self._sink = sink

    def run(self) -> tuple[Path, ...]:
        """Write one FASTA file per accession longer than the cutoff."""
        paths: list[Path] = []
        for accession in self._accessions.read():
            record = self._source.fetch(accession)
            sequence = record.seq
            length = 0 if sequence is None else len(str(sequence))
            if not self._cutoff.accepts(length):
                continue
            paths.append(self._sink.write(self._encoder.encode(accession, record)))
        if not paths:
            raise NcbiRecordRejected("every accession was at or below the cutoff")
        return tuple(paths)
