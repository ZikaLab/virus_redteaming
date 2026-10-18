"""Choose one VMR isolate for each virus name."""

from __future__ import annotations

from virus_redteaming.nen_accession.models import VmrIsolate, cleaned_virus_name


class ExemplarVirusIndex:
    """First exemplar wins. A name with no exemplar keeps the first row."""

    def __init__(self, isolates: tuple[VmrIsolate, ...]) -> None:
        chosen: dict[str, VmrIsolate] = {}
        for isolate in isolates:
            key = cleaned_virus_name(isolate.virus_name)
            if not key:
                continue
            current = chosen.get(key)
            if current is None or (isolate.is_exemplar and not current.is_exemplar):
                chosen[key] = isolate
        self._chosen = chosen

    def isolate(self, nen_virus: str) -> VmrIsolate | None:
        return self._chosen.get(cleaned_virus_name(nen_virus))

class ExemplarIndexFactory:
    def build(self, isolates: tuple[VmrIsolate, ...]) -> ExemplarVirusIndex:
        return ExemplarVirusIndex(isolates)
