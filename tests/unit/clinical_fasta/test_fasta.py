"""FASTA identity, length cutoff, and download skipping."""

from pathlib import Path

import pytest
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from virus_redteaming.clinical_fasta.download_workflow import ClinicalFastaDownload
from virus_redteaming.clinical_fasta.errors import NcbiInputError, NcbiRecordRejected
from virus_redteaming.clinical_fasta.fasta_encoder import BiopythonFastaEncoder
from virus_redteaming.clinical_fasta.fasta_source import (
    AccessionIdentity,
    FastaFetchSource,
)
from virus_redteaming.clinical_fasta.length import LengthCutoff
from virus_redteaming.clinical_fasta.sink import AtomicPathFastaSink


class _Fetch:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[str] = []

    def fetch_fasta(self, accession: str) -> str:
        self.calls.append(accession)
        return self.text


class _Table:
    def __init__(self, accessions: tuple[str, ...]) -> None:
        self._accessions = accessions

    def read(self) -> tuple[str, ...]:
        return self._accessions


class _Source:
    def __init__(self, lengths: dict[str, int]) -> None:
        self._lengths = lengths

    def fetch(self, accession: str) -> SeqRecord:
        return SeqRecord(Seq("A" * self._lengths[accession]), id=accession)


def test_download_writes_all_five_mitochondrion_genomes(tmp_path: Path) -> None:
    ids = (
        "CM200698.1",
        "OZ567094.1",
        "OZ567093.1",
        "OZ560341.1",
        "OZ561974.1",
    )
    paths = ClinicalFastaDownload(
        _Table(ids),
        _Source({accession: 16569 for accession in ids}),
        LengthCutoff(),
        BiopythonFastaEncoder(),
        AtomicPathFastaSink(tmp_path),
    ).run()
    assert [path.name for path in paths] == [f"{accession}.fasta" for accession in ids]


def test_download_fetches_each_distinct_accession_as_fasta(tmp_path: Path) -> None:
    from virus_redteaming.clinical_fasta.accession_source import AccessionCsvSource

    table = tmp_path / "accessions.csv"
    table.write_text("Accession\nA1\nA2\nA1\n", encoding="utf-8")
    calls: list[str] = []

    class _Distinct:
        def fetch_fasta(self, accession: str) -> str:
            calls.append(accession)
            return f">{accession}\nACGT\n"

    source = FastaFetchSource(_Distinct(), AccessionIdentity())
    for accession in AccessionCsvSource(table).read():
        source.fetch(accession)
    assert calls == ["A1", "A2"]


def test_fasta_source_accepts_one_matching_record() -> None:
    client = _Fetch(">NG_1 synthetic\nACGT\n")
    record = FastaFetchSource(client, AccessionIdentity()).fetch("NG_1")
    assert record.id == "NG_1"
    assert client.calls == ["NG_1"]


def test_fasta_identity_accepts_version_and_bar_token() -> None:
    identity = AccessionIdentity()
    versioned = SeqRecord(Seq("A"), id="NG_007114.1")
    barred = SeqRecord(Seq("A"), id="ref|NG_007114.1|")
    other = SeqRecord(Seq("A"), id="NG_007114.2")
    doubled = SeqRecord(Seq("A"), id="NG_007114.1.2")
    assert identity.matches(versioned, "NG_007114") is True
    assert identity.matches(barred, "NG_007114") is True
    assert identity.matches(other, "NG_007114.1") is False
    assert identity.matches(doubled, "NG_007114.1") is False


def test_fasta_source_rejects_wrong_count_or_id() -> None:
    identity = AccessionIdentity()
    with pytest.raises(NcbiRecordRejected):
        FastaFetchSource(_Fetch(""), identity).fetch("NG_1")
    with pytest.raises(NcbiRecordRejected):
        FastaFetchSource(_Fetch(">NG_1\nA\n>NG_2\nC\n"), identity).fetch("NG_1")
    with pytest.raises(NcbiRecordRejected):
        FastaFetchSource(_Fetch(">OTHER\nAC\n"), identity).fetch("NG_1")
    with pytest.raises(NcbiRecordRejected):
        FastaFetchSource(_Fetch(">NG_1\n\n"), identity).fetch("NG_1")


def test_length_cutoff_default_is_7000_and_is_exclusive() -> None:
    cutoff = LengthCutoff()
    assert cutoff.DEFAULT_BP == 7000
    assert cutoff.MAX_SLEN == 999_999_999
    assert cutoff.accepts(7000) is False
    assert cutoff.accepts(7001) is True
    assert cutoff.slen_clause() == "7001:999999999[SLEN]"


def test_download_min_length_overrides_default(tmp_path: Path) -> None:
    download = ClinicalFastaDownload(
        _Table(("SHORT", "LONG")),
        _Source({"SHORT": 9000, "LONG": 10001}),
        LengthCutoff(bp=10000),
        BiopythonFastaEncoder(),
        AtomicPathFastaSink(tmp_path),
    )
    paths = download.run()
    assert [path.name for path in paths] == ["LONG.fasta"]
    assert LengthCutoff.DEFAULT_BP == 7000


def test_download_skips_short_records_and_fails_when_none_remain(
    tmp_path: Path,
) -> None:
    mixed = ClinicalFastaDownload(
        _Table(("SHORT", "LONG")),
        _Source({"SHORT": 10, "LONG": 20}),
        LengthCutoff(bp=15),
        BiopythonFastaEncoder(),
        AtomicPathFastaSink(tmp_path),
    )
    assert [path.name for path in mixed.run()] == ["LONG.fasta"]
    with pytest.raises(NcbiRecordRejected):
        ClinicalFastaDownload(
            _Table(("SHORT",)),
            _Source({"SHORT": 10}),
            LengthCutoff(bp=15),
            BiopythonFastaEncoder(),
            AtomicPathFastaSink(tmp_path / "none"),
        ).run()
    assert list((tmp_path / "none").glob("*.fasta")) == []


def test_download_rejects_malformed_accession(tmp_path: Path) -> None:
    from virus_redteaming.clinical_fasta.accession_source import AccessionCsvSource

    path = tmp_path / "accessions.csv"
    path.write_text("Accession\nnot an id\n", encoding="utf-8")
    with pytest.raises(NcbiInputError):
        AccessionCsvSource(path).read()
