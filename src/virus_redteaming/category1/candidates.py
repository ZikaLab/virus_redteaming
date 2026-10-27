"""ICTV genera a genus prompt is allowed to return."""

from __future__ import annotations

from virus_redteaming.category1.inventory import IctvGenusInventory, unique_strings
from virus_redteaming.category1.models import CatalogueVirus

_STEM_MIN = 6


class GenusCandidateList:
    def candidates(
        self,
        row: CatalogueVirus,
        inventory: IctvGenusInventory,
    ) -> tuple[str, ...]:
        in_family: list[str] = []
        if row.family in inventory.families():
            seen: set[str] = set()
            for species in inventory.rows:
                if species.family != row.family or species.genus == "":
                    continue
                if species.genus not in seen:
                    seen.add(species.genus)
                    in_family.append(species.genus)
        stem = row.genus.casefold()
        if row.genus in in_family or len(stem) < _STEM_MIN:
            by_stem: tuple[str, ...] = ()
        else:
            by_stem = tuple(
                genus
                for genus in inventory.genera()
                if stem in genus.casefold() and genus not in in_family
            )
        return unique_strings([*in_family, *by_stem])
