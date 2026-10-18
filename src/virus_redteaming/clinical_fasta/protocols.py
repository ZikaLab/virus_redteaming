"""Seams for search and FASTA retrieval. Callers depend on these, not on Biopython."""

from pathlib import Path
from typing import Protocol

from Bio.SeqRecord import SeqRecord

from virus_redteaming.clinical_fasta.models import (
    AccessionHit,
    ChosenAccession,
    CriteriaRow,
    FastaRecord,
    MeasuredFasta,
)


class VirusQuerySource(Protocol):
    """Reads trimmed query cells."""

    def read(self) -> tuple[str, ...]:
        """Return non-blank query cells in file order."""


class SearchTermSource(Protocol):
    """Reads the extra search term."""

    def read(self) -> str:
        """Return the single extra term."""


class NucleotideSearcher(Protocol):
    """Searches nuccore."""

    def search(self, term: str) -> tuple[str, ...]:
        """Return accession ids in NCBI order."""


class AccessionTableSink(Protocol):
    """Persists accession hits."""

    def write(self, hits: tuple[AccessionHit, ...] | list[AccessionHit]) -> Path:
        """Replace the accession table and return its path."""


class AccessionTableSource(Protocol):
    """Reads distinct accessions."""

    def read(self) -> tuple[str, ...]:
        """Return distinct accessions in first-seen order."""


class NucleotideFetch(Protocol):
    """Fetches one FASTA body. The handle is already closed."""

    def fetch_fasta(self, accession: str) -> str:
        """Return FASTA text for one accession."""


class FastaRecordSource(Protocol):
    """Parses one validated FASTA record."""

    def fetch(self, accession: str) -> SeqRecord:
        """Return the single record for this accession."""


class FastaEncoder(Protocol):
    """Encodes a record under the requested accession."""

    def encode(self, accession: str, record: SeqRecord) -> FastaRecord:
        """Return FASTA text labelled with the requested accession."""


class AccessionGroupSource(Protocol):
    """Reads Virus, Rank, and Accession in file order."""

    def read(self) -> tuple[AccessionHit, ...]:
        """Return every accession row, including repeated query cells."""


class FastaMeasure(Protocol):
    """Reads one local FASTA file."""

    def read(self, path: Path) -> MeasuredFasta | None:
        """Return the measurement, or None when the file is absent."""


class CriteriaSink(Protocol):
    """Persists the criteria table."""

    def write(self, rows: tuple[CriteriaRow, ...] | list[CriteriaRow]) -> Path:
        """Replace the criteria table and return its path."""


class RepresentativeSink(Protocol):
    """Persists chosen sequences."""

    def write(self, rows: tuple[CriteriaRow, ...] | list[CriteriaRow]) -> Path:
        """Replace the representative table and return its path."""


class CriteriaRepresentativeSource(Protocol):
    """Reads chosen rows from a criteria table."""

    def read(self) -> tuple[ChosenAccession, ...]:
        """Return one chosen accession per trimmed query."""


class CriteriaRepresentativeOpener(Protocol):
    """Opens a criteria reader for a path known only after the write."""

    def open(self, path: Path) -> CriteriaRepresentativeSource:
        """Return a reader bound to the written criteria file."""


class GenesAligner(Protocol):
    """Copies chosen accessions onto the query table."""

    def write(self, chosen: tuple[ChosenAccession, ...]) -> Path:
        """Replace the query table and return its path."""


class FastaSink(Protocol):
    """Persists one FASTA file."""

    def write(self, record: FastaRecord) -> Path:
        """Replace one FASTA file and return its path."""
