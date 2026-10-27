"""Stack HSE rows, then Category 1 rows, into one schema."""

from __future__ import annotations

from virus_redteaming.hse_cat1_merge.models import (
    Cat1VirusRow,
    HseVirusRow,
    MergedVirusRow,
)
from virus_redteaming.hse_cat1_merge.vmr import VmrTaxonIndex
from virus_redteaming.nen_accession.models import cleaned_virus_name
from virus_redteaming.nen_accession.protocols import AccessionParser


class HseCat1Merger:
    def __init__(self, index: VmrTaxonIndex, parser: AccessionParser) -> None:
        self._index = index
        self._parser = parser

    def merge(
        self,
        hse_rows: tuple[HseVirusRow, ...],
        cat1_rows: tuple[Cat1VirusRow, ...],
    ) -> tuple[MergedVirusRow, ...]:
        hse = tuple(self._from_hse(row) for row in hse_rows)
        cat1 = tuple(self._from_cat1(row) for row in cat1_rows)
        return hse + cat1

    def _from_hse(self, row: HseVirusRow) -> MergedVirusRow:
        taxon = None
        if cleaned_virus_name(row.nen_virus):
            taxon = self._index.taxon(row.nen_virus)
        return MergedVirusRow(
            source="HSE",
            catalogue_family=row.family,
            catalogue_genus=row.genus,
            catalogue_virus=row.viruses,
            ictv_family=taxon.family if taxon else "",
            ictv_genus=row.nen_genus,
            ictv_virus=row.nen_virus,
            species=taxon.species if taxon else "",
            kingdom=taxon.kingdom if taxon else "",
            genbank_accessions=taxon.genbank_field if taxon else "",
            ncbi_accession=row.ncbi_accession,
            refseq_accessions="",
            hazard_group=row.hazard_group,
            schedule_5=row.schedule_5,
            issues=row.issues,
        )

    def _from_cat1(self, row: Cat1VirusRow) -> MergedVirusRow:
        return MergedVirusRow(
            source="Cat1",
            catalogue_family="",
            catalogue_genus="",
            catalogue_virus="",
            ictv_family=row.family,
            ictv_genus=row.genus,
            ictv_virus=row.exemplar,
            species=row.species,
            kingdom=row.kingdom,
            genbank_accessions=row.genbank,
            ncbi_accession=self._parser.join(row.genbank),
            refseq_accessions=row.refseq,
            hazard_group=row.hazard_group,
            schedule_5=row.schedule_5,
            issues=row.issues,
        )
