"""CSV writers and the nen reader used by sampling."""

from __future__ import annotations

import csv
from pathlib import Path

from virus_redteaming.category1.models import Cat1Row, IctvSpecies, NenRow

NEN_HEADER: tuple[str, ...] = (
    "Family",
    "Genus",
    "NEN genus",
    "Viruses",
    "NEN virus",
    "Issues",
)

CAT1_HEADER: tuple[str, ...] = (
    "Species",
    "Exemplar virus",
    "Family",
    "Genus",
    "Kingdom",
    "GenBank accessions",
    "RefSeq accessions",
    "Human pathogen hazard group",
    "Schedule 5",
    "Issues",
)


class NenWriter:
    def write(self, path: Path, nen_rows: tuple[NenRow, ...]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(NEN_HEADER)
            for row in nen_rows:
                writer.writerow(
                    (
                        row.family,
                        row.genus,
                        row.nen_genus,
                        row.viruses,
                        row.nen_virus,
                        row.issues,
                    )
                )


class NenReader:
    """Contiguous repeats of Family, Genus, and Viruses share one catalogue index."""

    def read(self, path: Path) -> tuple[NenRow, ...]:
        rows: list[NenRow] = []
        previous: tuple[str, str, str] | None = None
        next_index = -1
        with path.open(encoding="utf-8", newline="") as handle:
            for record in csv.DictReader(handle):
                key = (record["Family"], record["Genus"], record["Viruses"])
                if key != previous:
                    next_index += 1
                    previous = key
                rows.append(
                    NenRow(
                        catalogue_index=next_index,
                        family=record["Family"],
                        genus=record["Genus"],
                        nen_genus=record["NEN genus"],
                        viruses=record["Viruses"],
                        nen_virus=record["NEN virus"],
                        issues=record["Issues"],
                    )
                )
        return tuple(rows)


class IctvCat1Writer:
    def write(self, path: Path, species_rows: tuple[IctvSpecies, ...]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(CAT1_HEADER)
            for species in species_rows:
                row = Cat1Row.from_species(species)
                writer.writerow(
                    (
                        row.species,
                        row.exemplar,
                        row.family,
                        row.genus,
                        row.kingdom,
                        row.genbank,
                        row.refseq,
                        row.hazard_group,
                        row.schedule_5,
                        row.issues,
                    )
                )
