"""Records passed between the VMR index and the nen writer."""

from __future__ import annotations

from dataclasses import dataclass


def cleaned_virus_name(value: str) -> str:
    """Drop a non-breaking space and surrounding whitespace. Keep case."""
    return value.replace("\xa0", " ").strip()


@dataclass(frozen=True)
class VmrIsolate:
    virus_name: str
    is_exemplar: bool
    genbank_field: str


@dataclass(frozen=True)
class NenVirusRecord:
    family: str
    genus: str
    nen_genus: str
    viruses: str
    nen_virus: str
    hazard_group: str
    schedule_5: str
    issues: str
    ncbi_accession: str = ""

    def with_ncbi(self, ncbi_accession: str) -> NenVirusRecord:
        return NenVirusRecord(
            family=self.family,
            genus=self.genus,
            nen_genus=self.nen_genus,
            viruses=self.viruses,
            nen_virus=self.nen_virus,
            hazard_group=self.hazard_group,
            schedule_5=self.schedule_5,
            issues=self.issues,
            ncbi_accession=ncbi_accession,
        )


@dataclass(frozen=True)
class AssignmentReport:
    matched: int
    unmatched_names: tuple[str, ...]
    blank_nen_virus: int
