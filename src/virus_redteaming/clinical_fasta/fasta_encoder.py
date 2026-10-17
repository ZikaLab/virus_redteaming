"""Encode one SeqRecord. The stored accession is the requested id, not record.id."""

from io import StringIO

from Bio import SeqIO
from Bio.SeqRecord import SeqRecord

from virus_redteaming.clinical_fasta.models import FastaRecord


class BiopythonFastaEncoder:
    """The only type that calls Bio.SeqIO.write."""

    def encode(self, accession: str, record: SeqRecord) -> FastaRecord:
        """Return FASTA text that ends with one newline."""
        buffer = StringIO()
        SeqIO.write(record, buffer, "fasta")
        text = buffer.getvalue()
        if not text.endswith("\n"):
            text += "\n"
        return FastaRecord(accession=accession, text=text)
