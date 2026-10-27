"""Readers for the catalogue and the ICTV RNA table."""

from __future__ import annotations

import csv
from pathlib import Path

from virus_redteaming.category1.models import CatalogueVirus, IctvSpecies


def unique_strings(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return tuple(ordered)


class CatalogueGenusIndex:
    """Read Family, Genus, and Virus. Hazard group and Schedule 5 are ignored."""

    def read(self, path: Path) -> tuple[CatalogueVirus, ...]:
        rows: list[CatalogueVirus] = []
        with path.open(encoding="utf-8", newline="") as handle:
            for index, record in enumerate(csv.DictReader(handle)):
                rows.append(
                    CatalogueVirus(
                        catalogue_index=index,
                        family=record["Family"],
                        genus=record["Genus"],
                        virus=record["Virus"],
                    )
                )
        return tuple(rows)


class IctvGenusInventory:
    """ICTV species in file order, indexed by genus."""

    def __init__(self, rows: tuple[IctvSpecies, ...]) -> None:
        self.rows = rows

    @classmethod
    def from_csv(cls, path: Path) -> IctvGenusInventory:
        rows: list[IctvSpecies] = []
        with path.open(encoding="utf-8", newline="") as handle:
            for index, record in enumerate(csv.DictReader(handle)):
                rows.append(
                    IctvSpecies(
                        source_index=index,
                        species=record["Species"],
                        exemplar=record["Exemplar virus"],
                        family=record["Family"],
                        genus=record["Genus"],
                        kingdom=record["Kingdom"],
                        genbank=record["GenBank accessions"],
                        refseq=record["RefSeq accessions"],
                    )
                )
        return cls(tuple(rows))

    def genera(self) -> tuple[str, ...]:
        return unique_strings([row.genus for row in self.rows if row.genus != ""])

    def by_genus(self, genus: str) -> tuple[IctvSpecies, ...]:
        return tuple(row for row in self.rows if row.genus == genus)

    def exemplars(self, genus: str) -> tuple[str, ...]:
        return unique_strings([row.exemplar for row in self.by_genus(genus)])

    def families(self) -> frozenset[str]:
        return frozenset(row.family for row in self.rows)
