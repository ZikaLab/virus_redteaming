"""Treat a local FASTA file as cached when its header matches the accession."""

from pathlib import Path

from Bio import SeqIO

from virus_redteaming.clinical_fasta.fasta_source import AccessionIdentity


class DirectoryFastaCache:
    """Looks up ``{directory}/{accession}.fasta``."""

    def __init__(self, directory: Path, identity: AccessionIdentity) -> None:
        self._directory = directory
        self._identity = identity

    def cached(self, accession: str) -> Path | None:
        """Return the file when it is one matching non-empty FASTA record."""
        path = self._directory / f"{accession}.fasta"
        if not path.is_file():
            return None
        try:
            with path.open(encoding="utf-8") as handle:
                records = list(SeqIO.parse(handle, "fasta"))  # type: ignore[no-untyped-call]
        except Exception:
            return None
        if len(records) != 1:
            return None
        record = records[0]
        if len(record.seq) == 0 or not self._identity.matches(record, accession):
            return None
        return path
