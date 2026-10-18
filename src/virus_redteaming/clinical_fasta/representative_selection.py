"""Pick one representative inside an already scored group."""

from dataclasses import replace

from virus_redteaming.clinical_fasta.models import CriteriaRow

UPPER_BP = 40_000


class RepresentativeSelection:
    """Applies in-order, adjacent, word count, continuation, length, then rank."""

    def choose(self, rows: tuple[CriteriaRow, ...]) -> tuple[CriteriaRow, ...]:
        """Mark the winning row. Eligible losers keep an empty Failure."""
        eligible = [row for row in rows if row.failure == ""]
        in_order = [row for row in eligible if row.in_order]
        if in_order:
            pool = in_order
            adjacent = [row for row in pool if row.adjacent]
            if adjacent:
                pool = adjacent
        else:
            counts = [
                row.word_match_count for row in eligible if row.word_match_count > 0
            ]
            if not counts:
                return rows
            best = max(counts)
            pool = [row for row in eligible if row.word_match_count == best]
        winner = min(pool, key=_choice_key)
        return tuple(replace(row, representative=row is winner) for row in rows)


def _choice_key(row: CriteriaRow) -> tuple[int, int, int]:
    penalty = 0 if row.in_order else (row.match_continuation_penalty or 0)
    return (penalty, -(row.gene_length or 0), row.rank)
