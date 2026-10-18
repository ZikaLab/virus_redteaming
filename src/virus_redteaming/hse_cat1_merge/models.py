"""Rows read from the two source tables and written to the merge."""

from __future__ import annotations

from dataclasses import dataclass

MERGED_FIELDS: tuple[str, ...] = (
    "Source",
    "Catalogue family",
    "Catalogue genus",
    "Catalogue virus",
    "ICTV family",
    "ICTV genus",
    "ICTV virus",
    "Species",
    "Kingdom",
    "GenBank accessions",
    "NCBI accession",
    "RefSeq accessions",
    "Human pathogen hazard group",
    "Schedule 5",
    "Issues",
)


@dataclass(frozen=True)
class HseVirusRow:
    family: str
    genus: str
    nen_genus: str
    viruses: str
    nen_virus: str
    ncbi_accession: str
    hazard_group: str
    schedule_5: str
    issues: str


@dataclass(frozen=True)
class Cat1VirusRow:
    species: str
    exemplar: str
    family: str
    genus: str
    kingdom: str
    genbank: str
    refseq: str
    hazard_group: str
    schedule_5: str
    issues: str


@dataclass(frozen=True)
class VmrTaxon:
    virus_name: str
    is_exemplar: bool
    family: str
    species: str
    kingdom: str
    genbank_field: str


@dataclass(frozen=True)
class MergedVirusRow:
    source: str
    catalogue_family: str
    catalogue_genus: str
    catalogue_virus: str
    ictv_family: str
    ictv_genus: str
    ictv_virus: str
    species: str
    kingdom: str
    genbank_accessions: str
    ncbi_accession: str
    refseq_accessions: str
    hazard_group: str
    schedule_5: str
    issues: str

    def as_tuple(self) -> tuple[str, ...]:
        return (
            self.source,
            self.catalogue_family,
            self.catalogue_genus,
            self.catalogue_virus,
            self.ictv_family,
            self.ictv_genus,
            self.ictv_virus,
            self.species,
            self.kingdom,
            self.genbank_accessions,
            self.ncbi_accession,
            self.refseq_accessions,
            self.hazard_group,
            self.schedule_5,
            self.issues,
        )
