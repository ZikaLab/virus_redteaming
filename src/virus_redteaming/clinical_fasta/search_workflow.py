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
        composer: EntrezTermComposer,
        searcher: NucleotideSearcher,
        accession_list: AccessionList,
        cutoff: LengthCutoff,
        sink: AccessionTableSink,
    ) -> None:
        self._viruses = viruses
        self._extra_term = extra_term
        self._composer = composer
        self._searcher = searcher
        self._accession_list = accession_list
        self._cutoff = cutoff
        self._sink = sink

    def run(self) -> SearchResult:
        """Write hits. Return every Virus cell that came back empty."""
        extra = self._extra_term.read()
        hits: list[AccessionHit] = []
        misses: list[str] = []
        for virus in self._viruses.read():
            term = self._composer.compose(virus, extra, self._cutoff)
            ids = self._accession_list.keep(self._searcher.search(term))
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
