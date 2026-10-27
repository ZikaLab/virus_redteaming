"""NcbiFastaDownload coordinates injected protocols and stops on a fetch error."""

from pathlib import Path

import pytest
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from virus_redteaming.clinical_fasta.errors import NcbiRecordRejected
from virus_redteaming.clinical_fasta.models import FastaRecord
from virus_redteaming.ncbi_fasta.models import GenBankTableScan
from virus_redteaming.ncbi_fasta.workflow import NcbiFastaDownload


class _Source:
    def __init__(self, scan: GenBankTableScan) -> None:
        self._scan = scan
        self.reads = 0

    def read(self) -> GenBankTableScan:
        self.reads += 1
        return self._scan


class _Cache:
    def __init__(self, hits: dict[str, Path | None]) -> None:
        self._hits = hits
        self.calls: list[str] = []

    def cached(self, accession: str) -> Path | None:
        self.calls.append(accession)
        return self._hits[accession]


class _Records:
    def __init__(self, fail_on: str | None = None) -> None:
        self._fail_on = fail_on
        self.calls: list[str] = []

    def fetch(self, accession: str) -> SeqRecord:
        self.calls.append(accession)
        if accession == self._fail_on:
            raise NcbiRecordRejected(accession)
        return SeqRecord(Seq("ACGT"), id=accession)


class _Encoder:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def encode(self, accession: str, record: SeqRecord) -> FastaRecord:
        self.calls.append(accession)
        return FastaRecord(accession, f">{accession}\n{record.seq}\n")


class _Sink:
    def __init__(self, root: Path) -> None:
        self._root = root
        self.calls: list[str] = []

    def write(self, record: FastaRecord) -> Path:
        self.calls.append(record.accession)
        return self._root / f"{record.accession}.fasta"


def test_protocol_fakes_skip_cached_codes_and_stop_on_fetch_error(
    tmp_path: Path,
) -> None:
    cached = tmp_path / "V00603.fasta"
    source = _Source(GenBankTableScan(("V00603", "J02151", "U87411"), 2))
    cache = _Cache({"V00603": cached, "J02151": None, "U87411": None})
    records = _Records(fail_on="J02151")
    encoder = _Encoder()
    sink = _Sink(tmp_path)
    download = NcbiFastaDownload(source, cache, records, encoder, sink)
    with pytest.raises(NcbiRecordRejected):
        download.run()
    assert source.reads == 1
    assert cache.calls == ["V00603", "J02151"]
    assert records.calls == ["J02151"]
    assert encoder.calls == []
    assert sink.calls == []
