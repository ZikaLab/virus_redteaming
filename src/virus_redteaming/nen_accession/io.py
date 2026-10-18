"""CSV adapters for the VMR and the nen table."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path

from virus_redteaming.nen_accession.errors import NenTableError, VmrTableError
from virus_redteaming.nen_accession.models import NenVirusRecord, VmrIsolate

NEN_FIELDS: tuple[str, ...] = (
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

_NEN_REQUIRED: tuple[str, ...] = (
    "Family",
    "Genus",
    "NEN genus",
    "Viruses",
    "NEN virus",
    "Human pathogen hazard group",
    "Schedule 5",
    "Issues",
)

_VMR_NAME = "Virus name(s)"
_VMR_EXEMPLAR = "Exemplar or additional isolate"
_VMR_ACCESSION = "Virus GENBANK accession"
_VMR_REQUIRED: tuple[str, ...] = (_VMR_NAME, _VMR_EXEMPLAR, _VMR_ACCESSION)


class VmrCsvReader:
    def read(self, path: Path) -> tuple[VmrIsolate, ...]:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            self._require(reader.fieldnames)
            isolates = tuple(
                VmrIsolate(
                    virus_name=record[_VMR_NAME],
                    is_exemplar=record[_VMR_EXEMPLAR].strip() == "E",
                    genbank_field=record[_VMR_ACCESSION],
                )
                for record in reader
            )
        return isolates

    def _require(self, fieldnames: Sequence[str] | None) -> None:
        found = set(fieldnames or [])
        missing = [name for name in _VMR_REQUIRED if name not in found]
        if missing:
            raise VmrTableError(f"VMR CSV is missing {', '.join(missing)}")


class NenCsvReader:
    def read(self, path: Path) -> tuple[NenVirusRecord, ...]:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            self._require(reader.fieldnames)
            rows = tuple(
                NenVirusRecord(
                    family=record["Family"],
                    genus=record["Genus"],
                    nen_genus=record["NEN genus"],
                    viruses=record["Viruses"],
                    nen_virus=record["NEN virus"],
                    hazard_group=record["Human pathogen hazard group"],
                    schedule_5=record["Schedule 5"],
                    issues=record["Issues"],
                )
                for record in reader
            )
        return rows

    def _require(self, fieldnames: Sequence[str] | None) -> None:
        found = set(fieldnames or [])
        missing = [name for name in _NEN_REQUIRED if name not in found]
        if missing:
            raise NenTableError(f"nen CSV is missing {', '.join(missing)}")


class NenAccessionWriter:
    def write(self, path: Path, rows: tuple[NenVirusRecord, ...]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(NEN_FIELDS)
            for row in rows:
                writer.writerow(
                    (
                        row.family,
                        row.genus,
                        row.nen_genus,
                        row.viruses,
                        row.nen_virus,
                        row.ncbi_accession,
                        row.hazard_group,
                        row.schedule_5,
                        row.issues,
                    )
                )
