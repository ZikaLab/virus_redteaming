"""Sequence-length cutoff. Edit DEFAULT_BP and MAX_SLEN here when they change."""

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class LengthCutoff:
    """Keep a sequence only when it is longer than ``bp``.

    Change ``LengthCutoff.DEFAULT_BP`` in ``length.py`` when the default cutoff
    changes. Change ``LengthCutoff.MAX_SLEN`` in ``length.py`` when the search
    upper bound changes. ``search --min-length`` and ``download --min-length``
    override ``DEFAULT_BP`` for one run and do not edit ``DEFAULT_BP``.
    """

    DEFAULT_BP: ClassVar[int] = 8000
    MAX_SLEN: ClassVar[int] = 999_999_999
    bp: int = DEFAULT_BP

    def accepts(self, sequence_length: int) -> bool:
        """Return true when the sequence is longer than the cutoff."""
        return sequence_length > self.bp

    def slen_clause(self) -> str:
        """Return the Entrez range for sequences longer than the cutoff."""
        return f"{self.bp + 1}:{self.MAX_SLEN}[SLEN]"
