"""Resolve a query CSV under output/ and reject paths that leave that directory."""

from dataclasses import dataclass
from pathlib import Path

from virus_redteaming.clinical_fasta.errors import NcbiInputError

OUTPUT_DIRECTORY_NAME = "output"
DEFAULT_QUERY_FILENAME = "genes.csv"
SEARCH_TERM_FILENAME = "search.txt"
ACCESSION_FILENAME = "accessions.csv"
FASTA_DIRECTORY_NAME = "clinical_genes"
CRITERIA_FILENAME = "accession_criteria.csv"
REPRESENTATIVE_FILENAME = "NCBI_representative_seq.csv"


@dataclass(frozen=True)
class OutputCsvPath:
    """A bare filename resolved under ``output/``."""

    filename: str

    def resolve(self, root: Path | None = None) -> Path:
        """Return ``{root}/output/{filename}``."""
        self._reject(self.filename)
        base = root if root is not None else Path.cwd()
        return base / OUTPUT_DIRECTORY_NAME / self.filename

    @staticmethod
    def _reject(filename: str) -> None:
        if (
            not filename
            or filename.startswith(".")
            or filename.startswith("/")
            or filename.startswith("\\")
            or Path(filename).is_absolute()
            or "/" in filename
            or "\\" in filename
            or ".." in filename
        ):
            raise NcbiInputError(f"query filename is not allowed: {filename!r}")
