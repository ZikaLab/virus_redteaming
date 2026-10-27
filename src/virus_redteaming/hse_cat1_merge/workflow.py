"""Read both virus tables and the VMR, then write the merged CSV."""

from __future__ import annotations

from pathlib import Path

from virus_redteaming.hse_cat1_merge.io import (
    Cat1CsvReader,
    HseCsvReader,
    MergedCsvWriter,
    VmrTaxonReader,
)
from virus_redteaming.hse_cat1_merge.merge import HseCat1Merger
from virus_redteaming.hse_cat1_merge.order import MergedRowOrder
from virus_redteaming.hse_cat1_merge.vmr import VmrTaxonIndex
from virus_redteaming.nen_accession.protocols import AccessionParser


class MergeHseAndCat1:
    def __init__(
        self,
        hse_reader: HseCsvReader,
        cat1_reader: Cat1CsvReader,
        vmr_reader: VmrTaxonReader,
        writer: MergedCsvWriter,
        parser: AccessionParser,
        order: MergedRowOrder,
    ) -> None:
        self._hse_reader = hse_reader
        self._cat1_reader = cat1_reader
        self._vmr_reader = vmr_reader
        self._writer = writer
        self._parser = parser
        self._order = order

    def run(
        self,
        hse_path: Path,
        cat1_path: Path,
        vmr_path: Path,
        out_path: Path,
    ) -> int:
        hse_rows = self._hse_reader.read(hse_path)
        cat1_rows = self._cat1_reader.read(cat1_path)
        index = VmrTaxonIndex(self._vmr_reader.read(vmr_path))
        merged = HseCat1Merger(index, self._parser).merge(hse_rows, cat1_rows)
        ordered = self._order.sort(merged)
        self._writer.write(out_path, ordered)
        return len(ordered)
