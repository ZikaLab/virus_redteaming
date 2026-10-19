"""Split a GenBank cell into accession codes."""

from __future__ import annotations

import re

from virus_redteaming.ncbi_fasta.errors import NcbiFastaInputError

_ACCESSION = re.compile(
    r"^(?:[A-Z]{2}_\d{6,9}|[A-Z]{2}\d{8}|[A-Z]{2}\d{6}|[A-Z]\d{5})(?:\.\d+)?$"
)
_COORDINATE = re.compile(r"\s*\(\d+\.\d+\)\s*$")


class GenBankSegmentParser:
    """Keeps the code after each colon and rejects a populated cell that fails."""

    def codes(self, cell: str) -> tuple[str, ...]:
        """Return distinct accessions in segment order."""
        text = cell.replace("\xa0", " ").strip()
        if not text:
            return ()
        pieces = text.split(";")
        if not pieces[-1].strip():
            pieces = pieces[:-1]
        seen: list[str] = []
        for piece in pieces:
            code = _code(piece)
            if code not in seen:
                seen.append(code)
        return tuple(seen)


def _code(piece: str) -> str:
    segment = piece.strip()
    if not segment:
        raise NcbiFastaInputError("GenBank cell has an empty segment")
    raw_code = segment
    if ":" in segment:
        label, raw_code = segment.split(":", 1)
        if not label.strip():
            raise NcbiFastaInputError("GenBank segment label is empty")
    code = _COORDINATE.sub("", raw_code.strip()).strip()
    if _ACCESSION.fullmatch(code) is None:
        raise NcbiFastaInputError(f"GenBank accession is not valid: {code}")
    return code
