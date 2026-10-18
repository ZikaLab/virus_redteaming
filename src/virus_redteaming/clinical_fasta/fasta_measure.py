"""Measure a local FASTA file. An absent file is missing, not an error."""

import re
from pathlib import Path

from virus_redteaming.clinical_fasta.errors import NcbiInputError
from virus_redteaming.clinical_fasta.models import MeasuredFasta

_TOKEN = re.compile(r"[^A-Za-z0-9]+")


class FastaMeasure:
    """Reads one FASTA file into a header and a residue string."""

    def read(self, path: Path) -> MeasuredFasta | None:
        """Return the measurement, or None when the file is absent."""
        if not path.is_file():
            return None
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        if not lines or not lines[0].startswith(">"):
            raise NcbiInputError(f"FASTA file has no header: {path}")
        if any(line.startswith(">") for line in lines[1:]):
            raise NcbiInputError(f"FASTA file has a second header: {path}")
        header = lines[0][1:]
        sequence = "".join(lines[1:])
        sequence = "".join(sequence.split())
        words = tuple(word.lower() for word in _TOKEN.split(header) if word)
        return MeasuredFasta(
            header=header,
            header_words=words,
            gene_length=len(sequence),
            sequence=sequence,
        )
