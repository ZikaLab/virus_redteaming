"""EXCEPT inside NEN genus, then the first N(G) remainder rows."""

from __future__ import annotations

from virus_redteaming.category1.inventory import IctvGenusInventory
from virus_redteaming.category1.models import IctvSpecies, NenRow


class GenusVirusExcept:
    def remainder(
        self,
        inventory: IctvGenusInventory,
        nen_rows: tuple[NenRow, ...],
    ) -> dict[str, tuple[IctvSpecies, ...]]:
        genera = _nen_genera(nen_rows)
        result: dict[str, tuple[IctvSpecies, ...]] = {}
        for genus in genera:
            offered = set(inventory.exemplars(genus))
            remove = {
                row.nen_virus
                for row in nen_rows
                if row.nen_genus == genus and row.nen_virus in offered
            }
            result[genus] = tuple(
                species
                for species in inventory.by_genus(genus)
                if species.exemplar not in remove
            )
        return result


class GenusCategory1Sampler:
    def sample(
        self,
        nen_rows: tuple[NenRow, ...],
        remainder: dict[str, tuple[IctvSpecies, ...]],
    ) -> tuple[IctvSpecies, ...]:
        chosen: list[IctvSpecies] = []
        for genus in _nen_genera(nen_rows):
            count = len(
                {row.catalogue_index for row in nen_rows if row.nen_genus == genus}
            )
            chosen.extend(remainder.get(genus, ())[:count])
        return tuple(chosen)


def _nen_genera(nen_rows: tuple[NenRow, ...]) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for row in nen_rows:
        if row.nen_genus != "" and row.nen_genus not in seen:
            seen.add(row.nen_genus)
            ordered.append(row.nen_genus)
    return tuple(ordered)
