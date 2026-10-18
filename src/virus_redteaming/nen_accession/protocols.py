"""Seams for accession parsing and the virus-name index."""

from __future__ import annotations

from typing import Protocol

from virus_redteaming.nen_accession.models import VmrIsolate


class AccessionParser(Protocol):
    def join(self, genbank_field: str) -> str:
        """Return the NCBI accession codes from one GenBank cell."""


class VirusIndex(Protocol):
    def isolate(self, nen_virus: str) -> VmrIsolate | None:
        """Return the chosen VMR row for this NEN virus name."""


class VirusIndexFactory(Protocol):
    def build(self, isolates: tuple[VmrIsolate, ...]) -> VirusIndex:
        """Index isolates by virus name."""
