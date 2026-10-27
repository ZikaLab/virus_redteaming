"""CSV adapters for the merge inputs and the merged table."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path

from virus_redteaming.hse_cat1_merge.errors import MergeTableError
from virus_redteaming.hse_cat1_merge.models import (
    MERGED_FIELDS,
    Cat1VirusRow,
    HseVirusRow,
    MergedVirusRow,
    VmrTaxon,
)

_HSE_REQUIRED = (
    "Family",
    "Genus",
    "NEN genus",
    "Viruses",
    "NEN virus",
    "NCBI accession",
    "Human pathogen hazard group",
    "Schedule 5",
    "Issues",
)
_CAT1_REQUIRED = (
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
_VMR_REQUIRED = (
    "Virus name(s)",
    "Exemplar or additional isolate",
    "Family",
    "Species",
    "Kingdom",
    "Virus GENBANK accession",
)


def _require(
    fieldnames: Sequence[str] | None,
    required: tuple[str, ...],
    label: str,
) -> None:
    found = set(fieldnames or [])
    missing = [name for name in required if name not in found]
    if missing:
        raise MergeTableError(f"{label} is missing {', '.join(missing)}")


class HseCsvReader:
    def read(self, path: Path) -> tuple[HseVirusRow, ...]:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            _require(reader.fieldnames, _HSE_REQUIRED, "nen CSV")
            return tuple(
                HseVirusRow(
                    family=record["Family"],
                    genus=record["Genus"],
                    nen_genus=record["NEN genus"],
                    viruses=record["Viruses"],
                    nen_virus=record["NEN virus"],
                    ncbi_accession=record["NCBI accession"],
                    hazard_group=record["Human pathogen hazard group"],
                    schedule_5=record["Schedule 5"],
                    issues=record["Issues"],
                )
                for record in reader
            )


class Cat1CsvReader:
    def read(self, path: Path) -> tuple[Cat1VirusRow, ...]:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            _require(reader.fieldnames, _CAT1_REQUIRED, "Category 1 CSV")
            return tuple(
                Cat1VirusRow(
                    species=record["Species"],
                    exemplar=record["Exemplar virus"],
                    family=record["Family"],
                    genus=record["Genus"],
                    kingdom=record["Kingdom"],
                    genbank=record["GenBank accessions"],
                    refseq=record["RefSeq accessions"],
                    hazard_group=record["Human pathogen hazard group"],
                    schedule_5=record["Schedule 5"],
                    issues=record["Issues"],
                )
                for record in reader
            )


class VmrTaxonReader:
    def read(self, path: Path) -> tuple[VmrTaxon, ...]:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            _require(reader.fieldnames, _VMR_REQUIRED, "VMR CSV")
            return tuple(
                VmrTaxon(
                    virus_name=record["Virus name(s)"],
                    is_exemplar=record["Exemplar or additional isolate"].strip() == "E",
                    family=record["Family"],
                    species=record["Species"],
                    kingdom=record["Kingdom"],
                    genbank_field=record["Virus GENBANK accession"],
                )
                for record in reader
            )


class MergedCsvWriter:
    def write(self, path: Path, rows: tuple[MergedVirusRow, ...]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(MERGED_FIELDS)
            for row in rows:
                writer.writerow(row.as_tuple())
