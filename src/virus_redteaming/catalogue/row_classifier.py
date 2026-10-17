"""Classify a table row. One reason to change: source layout rules."""

from __future__ import annotations

import re
from enum import Enum

from virus_redteaming.catalogue.models import TableRow
from virus_redteaming.catalogue.text import collapse_whitespace, is_hazard_group


class RowKind(Enum):
    IGNORE = "ignore"
    SECTION_START = "section_start"
    SECTION_END = "section_end"
    FAMILY = "family"
    GENUS = "genus"
    FAMILY_AND_GENUS = "family_and_genus"
    AGENT = "agent"


_HEADER_EXACT = {
    "biological agent",
    "human pathogen",
    "hazard group",
    "taxonomy / notes",
    "health and safety executive",
}

_FAMILY = re.compile(r"\bFamily\s+(\S+)", re.IGNORECASE)
_GENUS = re.compile(r"\bGenus\s+(.+)$", re.IGNORECASE)


class RowClassifier:
    def classify(self, row: TableRow) -> RowKind:
        agent = collapse_whitespace(row.agent)
        hazard = collapse_whitespace(row.hazard_group)
        notes = collapse_whitespace(row.notes)
        if not agent and not hazard and not notes:
            return RowKind.IGNORE
        if self._is_chrome(agent, hazard, notes):
            return RowKind.IGNORE
        lowered = agent.casefold()
        if lowered.startswith("annex 1"):
            return RowKind.SECTION_END
        if lowered == "viruses":
            return RowKind.SECTION_START
        family = self.family_name(row.agent)
        genus = self.genus_name(row.agent)
        if family and genus:
            return RowKind.FAMILY_AND_GENUS
        if family:
            return RowKind.FAMILY
        if genus:
            return RowKind.GENUS
        if agent and is_hazard_group(hazard):
            return RowKind.AGENT
        return RowKind.IGNORE

    def family_name(self, agent: str) -> str:
        match = _FAMILY.search(collapse_whitespace(agent))
        return match.group(1).strip() if match else ""

    def genus_name(self, agent: str) -> str:
        collapsed = collapse_whitespace(agent)
        # Prefer the genus token on its own line when Family and Genus share a cell.
        for line in agent.replace("\r", "\n").split("\n"):
            match = _GENUS.search(collapse_whitespace(line))
            if match:
                return match.group(1).strip()
        match = _GENUS.search(collapsed)
        return match.group(1).strip() if match else ""

    def _is_chrome(self, agent: str, hazard: str, notes: str) -> bool:
        for part in (agent, hazard, notes):
            folded = part.casefold()
            if folded in _HEADER_EXACT:
                return True
            if folded.startswith("the approved list of biological agents"):
                return True
        return False
