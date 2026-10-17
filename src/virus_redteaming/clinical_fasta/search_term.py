"""Read the single extra term. The CLI passes output/search.txt."""

from pathlib import Path

from virus_redteaming.clinical_fasta.errors import NcbiInputError

_FORBIDDEN = set('"[]()')


class OutputSearchTermSource:
    """One non-empty line, with a trailing newline and surrounding space removed."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self) -> str:
        """Return the extra term."""
        if not self._path.is_file():
            raise NcbiInputError(f"search term file is missing: {self._path}")
        text = self._path.read_text(encoding="utf-8")
        if text.endswith("\n"):
            text = text[:-1]
        lines = text.split("\n")
        nonempty = [line.strip() for line in lines if line.strip()]
        if len(nonempty) != 1:
            raise NcbiInputError("search.txt must contain exactly one non-empty line")
        term = nonempty[0]
        if any(character in term for character in _FORBIDDEN):
            raise NcbiInputError("search.txt contains a forbidden character")
        return term
