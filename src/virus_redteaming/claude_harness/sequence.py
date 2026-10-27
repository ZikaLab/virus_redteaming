"""Copy the FASTA body, after the header line, into a sequence directory."""

import os
from pathlib import Path


def prepared_name(accession: str) -> str:
    """Return the file name written for ``accession``."""
    return f"{accession}.txt"


class FastaSequence:
    """Read ``{accession}.fasta`` from the source and write the body elsewhere."""

    def __init__(self, source: Path, destination: Path) -> None:
        self._source = source
        self._destination = destination

    def prepare(self, accession: str) -> Path | None:
        """Return the sequence path, or ``None`` when the FASTA cannot be used."""
        fasta = self._source / f"{accession}.fasta"
        target = self._destination / prepared_name(accession)
        try:
            text = fasta.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return None
        newline = text.find("\n")
        if newline < 0:
            return None
        header, body = text[:newline], text[newline + 1 :]
        if not header.startswith(">") or body == "":
            return None
        temporary = target.with_suffix(".txt.writing")
        try:
            self._destination.mkdir(parents=True, exist_ok=True)
            temporary.write_text(body, encoding="utf-8")
            os.replace(temporary, target)
        except OSError:
            temporary.unlink(missing_ok=True)
            return None
        return target
