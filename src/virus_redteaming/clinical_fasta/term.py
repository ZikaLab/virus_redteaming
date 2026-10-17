"""Compose an Entrez term from the query cell, the extra term, and the length cutoff."""

import re

from virus_redteaming.clinical_fasta.errors import NcbiInputError
from virus_redteaming.clinical_fasta.length import LengthCutoff

_FIELD = re.compile(r"(\[[^\[\]]+\])")
_BOOLEAN = re.compile(r"\b(?:AND|OR|NOT)\b", re.IGNORECASE)


class EntrezTermComposer:
    """Quotes a plain cell. A field flag such as ``[organism]`` stays outside quotes."""

    def compose(self, virus: str, extra: str, cutoff: LengthCutoff) -> str:
        """Return the nuccore term for one cell."""
        if '"' in virus:
            raise NcbiInputError("Virus cell contains a quote")
        cell = virus.strip()
        if "[" in cell or "]" in cell:
            return _flags_outside_quotes(cell)
        return f'"{cell}" AND {extra} AND {cutoff.slen_clause()}'


def _flags_outside_quotes(cell: str) -> str:
    if cell.count("[") != cell.count("]"):
        raise NcbiInputError("Virus cell has an unmatched field flag")
    parts = _FIELD.split(cell)
    rendered: list[str] = []
    index = 0
    while index < len(parts):
        text = parts[index]
        flag = parts[index + 1] if index + 1 < len(parts) else ""
        if flag.startswith("["):
            prefix, value = _value_before_flag(text)
            if not value:
                raise NcbiInputError("Virus cell has a field flag with no value")
            if prefix:
                rendered.append(prefix)
            rendered.append(f'"{value}"{flag}')
            index += 2
            continue
        free = text.strip()
        if free:
            rendered.append(free)
        index += 1
    return " ".join(rendered)


def _value_before_flag(text: str) -> tuple[str, str]:
    matches = list(_BOOLEAN.finditer(text))
    if not matches:
        return "", text.strip()
    last = matches[-1]
    return text[: last.end()].strip(), text[last.end() :].strip()
