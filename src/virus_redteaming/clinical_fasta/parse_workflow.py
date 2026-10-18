"""Score local FASTA files and align the chosen accessions onto genes.csv."""

from pathlib import Path

from virus_redteaming.clinical_fasta.header_match import HeaderMatch
from virus_redteaming.clinical_fasta.models import (
    AccessionHit,
    CriteriaRow,
    MeasuredFasta,
)
from virus_redteaming.clinical_fasta.protocols import (
    AccessionGroupSource,
    CriteriaRepresentativeOpener,
    CriteriaSink,
    FastaMeasure,
    GenesAligner,
    RepresentativeSink,
)
from virus_redteaming.clinical_fasta.representative_selection import (
    UPPER_BP,
    RepresentativeSelection,
)
from virus_redteaming.clinical_fasta.screened_words import ScreenedWords


class RepresentativeParse:
    """Groups, scores, and writes the three local files. It does not call NCBI."""

    def __init__(
        self,
        group_source: AccessionGroupSource,
        fasta_directory: Path,
        screened_words: ScreenedWords,
        measure: FastaMeasure,
        match: HeaderMatch,
        selection: RepresentativeSelection,
        criteria_sink: CriteriaSink,
        representative_sink: RepresentativeSink,
        representative_source: CriteriaRepresentativeOpener,
        genes_aligner: GenesAligner,
    ) -> None:
        self._group_source = group_source
        self._fasta_directory = fasta_directory
        self._screened_words = screened_words
        self._measure = measure
        self._match = match
        self._selection = selection
        self._criteria_sink = criteria_sink
        self._representative_sink = representative_sink
        self._representative_source = representative_source
        self._genes_aligner = genes_aligner

    def run(self) -> tuple[Path, Path, Path]:
        """Write the three outputs and return their paths."""
        hits = self._group_source.read()
        grouped = _groups(hits)
        scored: list[CriteriaRow] = []
        chosen_rows: list[CriteriaRow] = []
        for virus in _first_seen(hits):
            words = self._screened_words.from_query(virus)
            rows = tuple(self._score(hit, words) for hit in grouped[virus])
            selected = self._selection.choose(rows)
            scored.extend(selected)
            chosen_rows.extend(row for row in selected if row.representative)
        ordered = _in_hit_order(hits, scored)
        criteria_path = self._criteria_sink.write(tuple(ordered))
        representative_path = self._representative_sink.write(
            _first_seen_rows(hits, chosen_rows)
        )
        chosen = self._representative_source.open(criteria_path).read()
        genes_path = self._genes_aligner.write(chosen)
        return criteria_path, representative_path, genes_path

    def _score(self, hit: AccessionHit, words: tuple[str, ...]) -> CriteriaRow:
        measured = self._measure.read(self._fasta_directory / f"{hit.accession}.fasta")
        if not words:
            return _unmatched(hit, words, measured, "no screened words")
        if measured is None:
            return _unmatched(hit, words, None, "missing fasta")
        matched = self._match.matched_words(measured.header_words, words)
        in_order = self._match.in_order(measured.header_words, words)
        adjacent = self._match.adjacent(measured.header_words, words)
        failure = ""
        if measured.gene_length > UPPER_BP:
            failure = "longer than 40000 bp"
        elif not matched:
            failure = "no word match"
        return CriteriaRow(
            query=hit.virus,
            rank=hit.rank,
            accession=hit.accession,
            screened_words=words,
            in_order=in_order,
            adjacent=adjacent,
            word_match_count=len(matched),
            matched_words=matched,
            match_continuation_penalty=self._match.continuation_penalty(
                measured.header, matched
            ),
            gene_length=measured.gene_length,
            within_cutoff=measured.gene_length <= UPPER_BP,
            header=measured.header,
            failure=failure,
            representative=False,
            sequence=measured.sequence,
        )


def _groups(hits: tuple[AccessionHit, ...]) -> dict[str, list[AccessionHit]]:
    grouped: dict[str, list[AccessionHit]] = {}
    for hit in hits:
        grouped.setdefault(hit.virus, []).append(hit)
    return grouped


def _first_seen(hits: tuple[AccessionHit, ...]) -> tuple[str, ...]:
    seen: list[str] = []
    for hit in hits:
        if hit.virus not in seen:
            seen.append(hit.virus)
    return tuple(seen)


def _in_hit_order(
    hits: tuple[AccessionHit, ...], rows: list[CriteriaRow]
) -> tuple[CriteriaRow, ...]:
    by_key = {(row.query, row.rank, row.accession): row for row in rows}
    return tuple(by_key[(hit.virus, hit.rank, hit.accession)] for hit in hits)


def _first_seen_rows(
    hits: tuple[AccessionHit, ...], chosen: list[CriteriaRow]
) -> tuple[CriteriaRow, ...]:
    order = _first_seen(hits)
    by_query = {row.query: row for row in chosen}
    return tuple(by_query[query] for query in order if query in by_query)


def _unmatched(
    hit: AccessionHit,
    words: tuple[str, ...],
    measured: MeasuredFasta | None,
    failure: str,
) -> CriteriaRow:
    return CriteriaRow(
        query=hit.virus,
        rank=hit.rank,
        accession=hit.accession,
        screened_words=words,
        in_order=False,
        adjacent=False,
        word_match_count=0,
        matched_words=(),
        match_continuation_penalty=None if measured is None else 0,
        gene_length=None if measured is None else measured.gene_length,
        within_cutoff=measured is not None and measured.gene_length <= UPPER_BP,
        header="" if measured is None else measured.header,
        failure=failure,
        representative=False,
        sequence="" if measured is None else measured.sequence,
    )
