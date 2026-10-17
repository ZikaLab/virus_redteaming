"""Trim an IdList to five accessions."""

from virus_redteaming.clinical_fasta.errors import NcbiSearchMiss

_MAX_HITS = 5


class AccessionList:
    """Applies the size and emptiness rules for one search response."""

    def keep(self, ids: tuple[str, ...] | list[object]) -> tuple[str, ...]:
        """Return the first five ids, or an empty tuple when NCBI returned none."""
        if any(not isinstance(item, str) or not item for item in ids):
            raise NcbiSearchMiss("IdList item is not a non-empty string")
        kept = tuple(str(item) for item in ids[:_MAX_HITS])
        return kept
