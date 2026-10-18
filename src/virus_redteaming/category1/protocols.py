"""Prompt seams. Tests inject fakes. The CLI does not construct a model client."""

from __future__ import annotations

from typing import Protocol

from virus_redteaming.category1.models import CatalogueVirus


class GenusNenPrompt(Protocol):
    def choose(self, row: CatalogueVirus, candidates: tuple[str, ...]) -> str | None:
        """Return one offered ICTV genus, or none."""


class VirusNenPrompt(Protocol):
    def choose(
        self,
        nen_genus: str,
        virus: str,
        exemplars: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Return the offered exemplars in ``nen_genus`` that are this virus."""
