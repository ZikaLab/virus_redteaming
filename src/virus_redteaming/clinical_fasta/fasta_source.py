"""Match a requested accession to a FASTA header and parse one record."""

import re
from io import StringIO

from Bio import SeqIO
from Bio.SeqRecord import SeqRecord

from virus_redteaming.clinical_fasta.errors import NcbiRecordRejected
from virus_redteaming.clinical_fasta.protocols import NucleotideFetch

_TOKEN = re.compile(r"^(?P<stem>[A-Z]{1,6}_?[0-9]+)(?:\.(?P<version>[0-9]+))?$")


class AccessionIdentity:
    """Accepts an equal stem and, when both sides are versioned, an equal version."""

    def matches(self, record: SeqRecord, requested: str) -> bool:
        """Return true when a header token is the requested accession."""
        wanted = _parse(requested)
        if wanted is None:
            return False
        header = record.id or ""
        candidates = [header, *header.split("|")]
        if record.name:
            candidates.append(record.name)
        for token in candidates:
            parsed = _parse(token)
            if parsed is None or parsed[0] != wanted[0]:
                continue
            both_versioned = wanted[1] is not None and parsed[1] is not None
            versions_differ = both_versioned and wanted[1] != parsed[1]
            if versions_differ:
                continue
            return True
        return False


class FastaFetchSource:
    """Parses text from NucleotideFetch. It does not apply the length cutoff."""

    def __init__(self, client: NucleotideFetch, identity: AccessionIdentity) -> None:
        self._client = client
        self._identity = identity

    def fetch(self, accession: str) -> SeqRecord:
        """Return the single record whose header matches the accession."""
        text = self._client.fetch_fasta(accession)
        try:
            records = list(SeqIO.parse(StringIO(text), "fasta"))  # type: ignore[no-untyped-call]
        except Exception as exc:
            raise NcbiRecordRejected("FASTA text could not be parsed") from exc
        if len(records) != 1:
            raise NcbiRecordRejected("FASTA record count is not one")
        record = records[0]
        if not self._identity.matches(record, accession):
            raise NcbiRecordRejected("FASTA header does not match the accession")
        if len(record.seq) == 0:
            raise NcbiRecordRejected("FASTA sequence is empty")
        return record  # type: ignore[no-any-return]


def _parse(token: str) -> tuple[str, str | None] | None:
    match = _TOKEN.fullmatch(token)
    if match is None:
        return None
    return match.group("stem"), match.group("version")
