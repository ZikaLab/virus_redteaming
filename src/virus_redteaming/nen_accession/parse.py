"""Extract NCBI nucleotide accession codes from a VMR GenBank cell."""

from __future__ import annotations

import re

# Longer digit runs are tried first so an 8-digit accession is not cut to 6.
_ACCESSION = re.compile(
    r"(?:[A-Z]{2}_\d{6,9}|[A-Z]{2}\d{8}|[A-Z]{2}\d{6}|[A-Z]\d{5})(?:\.\d+)?"
)


class GenBankAccessionParser:
    """Keeps accession codes and drops segment labels and coordinate ranges."""

    def codes(self, genbank_field: str) -> tuple[str, ...]:
        text = genbank_field.replace("\xa0", " ")
        seen: list[str] = []
        for code in _ACCESSION.findall(text):
            if code not in seen:
                seen.append(code)
        return tuple(seen)

    def join(self, genbank_field: str) -> str:
        return "; ".join(self.codes(genbank_field))
