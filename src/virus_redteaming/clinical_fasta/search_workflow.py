"""Part 1. Empty cells are reported. A total miss does not publish the table."""

from virus_redteaming.clinical_fasta.accession_list import AccessionList
from virus_redteaming.clinical_fasta.errors import NcbiSearchMiss
from virus_redteaming.clinical_fasta.length import LengthCutoff
from virus_redteaming.clinical_fasta.models import AccessionHit, SearchResult
from virus_redteaming.clinical_fasta.protocols import (
    AccessionTableSink,
    NucleotideSearcher,
    SearchTermSource,
    VirusQuerySource,
)
from virus_redteaming.clinical_fasta.search_term import SearchTermAlternatives
from virus_redteaming.clinical_fasta.term import EntrezTermComposer


class AccessionSearch:
    """Sequences part 1. The docstring contains no query phrase.

    The length cutoff is ``LengthCutoff.DEFAULT_BP`` unless the caller passes
    another ``LengthCutoff``. ``MAX_SLEN`` lives beside it in ``length.py``.
    """

    def __init__(
        self,
        viruses: VirusQuerySource,
        extra_term: SearchTermSource,
        alternatives: SearchTermAlternatives,
        composer: EntrezTermComposer,
        searcher: NucleotideSearcher,
        accession_list: AccessionList,
        cutoff: LengthCutoff,
        sink: AccessionTableSink,
    ) -> None:
        self._viruses = viruses
        self._extra_term = extra_term
        self._alternatives = alternatives
        self._composer = composer
        self._searcher = searcher
        self._accession_list = accession_list
        self._cutoff = cutoff
        self._sink = sink

    def run(self) -> SearchResult:
        """Write hits. Return every Virus cell that came back empty."""
        alternatives = self._alternatives.split(self._extra_term.read())
        hits: list[AccessionHit] = []
        misses: list[str] = []
        for virus in self._viruses.read():
            ids = self._ids_for(virus, alternatives)
            if not ids:
                misses.append(virus)
                continue
            hits.extend(
                AccessionHit(virus=virus, rank=rank, accession=accession)
                for rank, accession in enumerate(ids, start=1)
            )
        if not hits:
            raise NcbiSearchMiss("every Virus cell returned no accessions")
        return SearchResult(path=self._sink.write(hits), misses=tuple(misses))

    def _ids_for(self, virus: str, alternatives: tuple[str, ...]) -> tuple[str, ...]:
        clause = self._cutoff.slen_clause()
        ids: tuple[str, ...] = ()
        for alternative in alternatives:
            term = self._composer.compose(virus, alternative, self._cutoff)
            ids = self._accession_list.keep(self._searcher.search(term))
            if ids or f"AND {alternative} AND {clause}" not in term:
                return ids
        return ids
