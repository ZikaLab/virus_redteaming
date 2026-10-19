"""Write the FASTA body, after the header line, to a ``.tmp`` file."""

import os
from pathlib import Path


class FastaSequence:
    """Read ``{accession}.fasta`` and replace ``{accession}.tmp``."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def prepare(self, accession: str) -> Path | None:
        """Return the ``.tmp`` path, or ``None`` when the sequence cannot be used."""
        source = self._directory / f"{accession}.fasta"
        target = self._directory / f"{accession}.tmp"
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return None
        newline = text.find("\n")
        if newline < 0:
            return None
        header, body = text[:newline], text[newline + 1 :]
        if not header.startswith(">") or body == "":
            return None
        temporary = target.with_suffix(".tmp.writing")
        try:
            temporary.write_text(body, encoding="utf-8")
            os.replace(temporary, target)
        except OSError:
            temporary.unlink(missing_ok=True)
            return None
        return target
