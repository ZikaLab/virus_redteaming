"""Values for the Category 1 genus join."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogueVirus:
    catalogue_index: int
    family: str
    genus: str
    virus: str


@dataclass(frozen=True)
class IctvSpecies:
    source_index: int
    species: str
    exemplar: str
    family: str
    genus: str
    kingdom: str
    genbank: str
    refseq: str


@dataclass(frozen=True)
class NenRow:
    catalogue_index: int
    family: str
    genus: str
    nen_genus: str
    viruses: str
    nen_virus: str
    issues: str


@dataclass(frozen=True)
class Cat1Row:
    species: str
    exemplar: str
    family: str
    genus: str
    kingdom: str
    genbank: str
    refseq: str
    hazard_group: str = "1"
    schedule_5: str = "0"
    issues: str = ""

    @classmethod
    def from_species(cls, species: IctvSpecies) -> Cat1Row:
        return cls(
            species=species.species,
            exemplar=species.exemplar,
            family=species.family,
            genus=species.genus,
            kingdom=species.kingdom,
            genbank=species.genbank,
            refseq=species.refseq,
        )
