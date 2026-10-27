"""Assign NEN genus and NEN virus. The only type that calls the prompts."""

from __future__ import annotations

from virus_redteaming.category1.candidates import GenusCandidateList
from virus_redteaming.category1.inventory import IctvGenusInventory
from virus_redteaming.category1.models import CatalogueVirus, NenRow
from virus_redteaming.category1.protocols import GenusNenPrompt, VirusNenPrompt


def is_catchall(virus: str) -> bool:
    text = virus.casefold()
    return "spp." in text or text.startswith("other ") or "species not listed" in text


def accept_genus(reply: str | None, candidates: tuple[str, ...]) -> str:
    if reply is not None and reply in candidates:
        return reply
    return ""


def accept_exemplars(
    reply_lines: tuple[str, ...],
    exemplars: tuple[str, ...],
) -> tuple[str, ...]:
    kept: list[str] = []
    for line in reply_lines:
        if line in exemplars and line not in kept:
            kept.append(line)
    return tuple(kept)


class NenHarmonizer:
    def __init__(
        self,
        candidates: GenusCandidateList,
        genus_prompt: GenusNenPrompt,
        virus_prompt: VirusNenPrompt,
    ) -> None:
        self._candidates = candidates
        self._genus_prompt = genus_prompt
        self._virus_prompt = virus_prompt

    def harmonize(
        self,
        catalogue: tuple[CatalogueVirus, ...],
        inventory: IctvGenusInventory,
    ) -> tuple[NenRow, ...]:
        rows: list[NenRow] = []
        for row in catalogue:
            rows.extend(self._harmonize_one(row, inventory))
        return tuple(rows)

    def _harmonize_one(
        self,
        row: CatalogueVirus,
        inventory: IctvGenusInventory,
    ) -> tuple[NenRow, ...]:
        genus_is_ictv = row.genus != "" and row.genus in inventory.genera()
        if genus_is_ictv:
            nen_genus = row.genus
            matches = self._ask_virus(row.virus, nen_genus, inventory)
            if not matches and not is_catchall(row.virus):
                alt = self._ask_genus(row, inventory)
                alt_matches = self._ask_virus(row.virus, alt, inventory)
                if alt != "" and alt_matches:
                    nen_genus = alt
                    matches = alt_matches
        else:
            nen_genus = self._ask_genus(row, inventory)
            matches = self._ask_virus(row.virus, nen_genus, inventory)
        return _emit(row, nen_genus, matches)

    def _ask_genus(self, row: CatalogueVirus, inventory: IctvGenusInventory) -> str:
        offered = self._candidates.candidates(row, inventory)
        reply = self._genus_prompt.choose(row, offered)
        return accept_genus(reply, offered)

    def _ask_virus(
        self,
        virus: str,
        nen_genus: str,
        inventory: IctvGenusInventory,
    ) -> tuple[str, ...]:
        if nen_genus == "":
            return ()
        offered = inventory.exemplars(nen_genus)
        reply = self._virus_prompt.choose(nen_genus, virus, offered)
        return accept_exemplars(reply, offered)


def _emit(
    row: CatalogueVirus,
    nen_genus: str,
    matches: tuple[str, ...],
) -> tuple[NenRow, ...]:
    if matches:
        return tuple(
            NenRow(
                catalogue_index=row.catalogue_index,
                family=row.family,
                genus=row.genus,
                nen_genus=nen_genus,
                viruses=row.virus,
                nen_virus=exemplar,
                issues="",
            )
            for exemplar in matches
        )
    if nen_genus == "":
        label = "genus not in ICTV"
    elif is_catchall(row.virus):
        label = "catchall"
    else:
        label = "unresolved name"
    return (
        NenRow(
            catalogue_index=row.catalogue_index,
            family=row.family,
            genus=row.genus,
            nen_genus=nen_genus,
            viruses=row.virus,
            nen_virus="",
            issues=label,
        ),
    )
