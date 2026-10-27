"""One VMR isolate per virus name, preferring the exemplar."""

from __future__ import annotations

from virus_redteaming.hse_cat1_merge.models import VmrTaxon
from virus_redteaming.nen_accession.models import cleaned_virus_name


class VmrTaxonIndex:
    def __init__(self, taxa: tuple[VmrTaxon, ...]) -> None:
        chosen: dict[str, VmrTaxon] = {}
        for taxon in taxa:
            key = cleaned_virus_name(taxon.virus_name)
            if not key:
                continue
            current = chosen.get(key)
            if current is None or (taxon.is_exemplar and not current.is_exemplar):
                chosen[key] = taxon
        self._chosen = chosen

    def taxon(self, virus_name: str) -> VmrTaxon | None:
        return self._chosen.get(cleaned_virus_name(virus_name))
