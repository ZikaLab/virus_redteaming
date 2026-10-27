"""Read the VMR and nen table, then write NCBI accessions back."""

from __future__ import annotations

from pathlib import Path

from virus_redteaming.nen_accession.assign import NenAccessionAssigner
from virus_redteaming.nen_accession.io import (
    NenAccessionWriter,
    NenCsvReader,
    VmrCsvReader,
)
from virus_redteaming.nen_accession.models import AssignmentReport
from virus_redteaming.nen_accession.protocols import AccessionParser, VirusIndexFactory


class AssignNenAccessions:
    def __init__(
        self,
        vmr_reader: VmrCsvReader,
        nen_reader: NenCsvReader,
        writer: NenAccessionWriter,
        parser: AccessionParser,
        index_factory: VirusIndexFactory,
    ) -> None:
        self._vmr_reader = vmr_reader
        self._nen_reader = nen_reader
        self._writer = writer
        self._parser = parser
        self._index_factory = index_factory

    def run(self, nen_path: Path, vmr_path: Path) -> AssignmentReport:
        isolates = self._vmr_reader.read(vmr_path)
        rows = self._nen_reader.read(nen_path)
        index = self._index_factory.build(isolates)
        updated, report = NenAccessionAssigner(index, self._parser).assign(rows)
        self._writer.write(nen_path, updated)
        return report
