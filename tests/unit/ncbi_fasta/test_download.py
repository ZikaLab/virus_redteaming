"""Cache hits skip Entrez. A fetched record is written under the requested code."""

from pathlib import Path

import pytest
from Bio import SeqIO

from virus_redteaming.clinical_fasta.errors import NcbiRecordRejected
from virus_redteaming.clinical_fasta.fasta_encoder import BiopythonFastaEncoder
from virus_redteaming.clinical_fasta.fasta_source import (
    AccessionIdentity,
    FastaFetchSource,
)
from virus_redteaming.clinical_fasta.sink import AtomicPathFastaSink
from virus_redteaming.ncbi_fasta.cache import DirectoryFastaCache
from virus_redteaming.ncbi_fasta.errors import NcbiFastaInputError
from virus_redteaming.ncbi_fasta.models import FetchNcbiFastaReport
from virus_redteaming.ncbi_fasta.parse import GenBankSegmentParser
from virus_redteaming.ncbi_fasta.source import MergedGenBankSource
from virus_redteaming.ncbi_fasta.workflow import NcbiFastaDownload


class _Bodies:
    def __init__(self, bodies: dict[str, str]) -> None:
        self.bodies = bodies
        self.calls: list[str] = []

    def fetch_fasta(self, accession: str) -> str:
        self.calls.append(accession)
        return self.bodies[accession]


def _table(path: Path, rows: str) -> None:
    path.write_text(f"GenBank accessions\n{rows}", encoding="utf-8")


def _run(
    table: Path,
    out: Path,
    bodies: dict[str, str],
) -> tuple[FetchNcbiFastaReport, _Bodies]:
    fetch = _Bodies(bodies)
    identity = AccessionIdentity()
    report = NcbiFastaDownload(
        source=MergedGenBankSource(table, GenBankSegmentParser()),
        cache=DirectoryFastaCache(out, identity),
        records=FastaFetchSource(fetch, identity),
        encoder=BiopythonFastaEncoder(),
        sink=AtomicPathFastaSink(out),
    ).run()
    return report, fetch


def test_valid_cached_fasta_file_is_a_cache_hit(tmp_path: Path) -> None:
    out = tmp_path / "fasta"
    out.mkdir()
    (out / "V00603.fasta").write_text(">V00603.1\nACGT\n", encoding="utf-8")
    table = tmp_path / "merged.csv"
    _table(table, "V00603\n")
    report, fetch = _run(table, out, {})
    assert fetch.calls == []
    assert report.cached == (out / "V00603.fasta",)
    assert report.written == ()


def test_header_only_or_mismatched_cached_file_is_refetched(tmp_path: Path) -> None:
    out = tmp_path / "fasta"
    out.mkdir()
    (out / "V00603.fasta").write_text(">V00603.1\n", encoding="utf-8")
    (out / "J02151.fasta").write_text(">U87411.1\nACGT\n", encoding="utf-8")
    table = tmp_path / "merged.csv"
    _table(table, "V00603\nJ02151\n")
    report, fetch = _run(
        table,
        out,
        {
            "V00603": ">V00603.1 influenza\nACGT\n",
            "J02151": ">J02151.1 influenza\nTTTT\n",
        },
    )
    assert fetch.calls == ["V00603", "J02151"]
    assert [path.name for path in report.written] == ["V00603.fasta", "J02151.fasta"]
    assert (out / "J02151.fasta").read_text(encoding="utf-8").startswith(">J02151.1")


def test_versioned_header_matches_unversioned_request(tmp_path: Path) -> None:
    table = tmp_path / "merged.csv"
    _table(table, "V00603\nAF291704\n")
    out = tmp_path / "fasta"
    report, fetch = _run(
        table,
        out,
        {
            "V00603": ">emb|V00603.1| influenza\nAC\n",
            "AF291704": ">AF291704.5 virus\nGG\n",
        },
    )
    assert fetch.calls == ["V00603", "AF291704"]
    v00603 = out / "V00603.fasta"
    assert report.written[0] == v00603
    assert v00603.read_text(encoding="utf-8").startswith(">emb|V00603.1|")
    af291704 = (out / "AF291704.fasta").read_text(encoding="utf-8")
    assert af291704.startswith(">AF291704.5")


def test_older_cached_version_is_a_hit(tmp_path: Path) -> None:
    out = tmp_path / "fasta"
    out.mkdir()
    cached = out / "AF291704.fasta"
    cached.write_text(">AF291704.1\nACGT\n", encoding="utf-8")
    table = tmp_path / "merged.csv"
    _table(table, "AF291704\n")
    report, fetch = _run(table, out, {})
    assert fetch.calls == []
    assert report.cached == (cached,)


def test_different_header_stem_is_rejected(tmp_path: Path) -> None:
    table = tmp_path / "merged.csv"
    _table(table, "V00603\n")
    out = tmp_path / "fasta"
    with pytest.raises(NcbiRecordRejected):
        _run(table, out, {"V00603": ">NC_002023.1 other\nACGT\n"})
    assert not (out / "V00603.fasta").exists()


def test_conflicting_versions_are_rejected(tmp_path: Path) -> None:
    table = tmp_path / "merged.csv"
    _table(table, "V00603.1\n")
    out = tmp_path / "fasta"
    with pytest.raises(NcbiRecordRejected):
        _run(table, out, {"V00603.1": ">V00603.2 influenza\nACGT\n"})
    assert not (out / "V00603.1.fasta").exists()


def test_short_sequence_is_written(tmp_path: Path) -> None:
    sequence = "A" * 2341
    table = tmp_path / "merged.csv"
    _table(table, "V00603\n")
    out = tmp_path / "fasta"
    report, _fetch = _run(table, out, {"V00603": f">V00603.1 influenza\n{sequence}\n"})
    written = report.written[0]
    record = next(SeqIO.parse(written, "fasta"))  # type: ignore[no-untyped-call]
    assert len(record.seq) == 2341


def test_missing_genbank_header_raises_input_error(tmp_path: Path) -> None:
    table = tmp_path / "merged.csv"
    table.write_text("Virus\nflu\n", encoding="utf-8")
    fetch = _Bodies({})
    identity = AccessionIdentity()
    download = NcbiFastaDownload(
        source=MergedGenBankSource(table, GenBankSegmentParser()),
        cache=DirectoryFastaCache(tmp_path, identity),
        records=FastaFetchSource(fetch, identity),
        encoder=BiopythonFastaEncoder(),
        sink=AtomicPathFastaSink(tmp_path),
    )
    with pytest.raises(NcbiFastaInputError):
        download.run()
    assert fetch.calls == []


def test_interrupted_run_resumes_without_refetching_earlier_files(
    tmp_path: Path,
) -> None:
    table = tmp_path / "merged.csv"
    _table(table, "RNA1: V00603; RNA2: J02151\n")
    out = tmp_path / "fasta"
    with pytest.raises(NcbiRecordRejected):
        _run(
            table,
            out,
            {
                "V00603": ">V00603.1 influenza\nACGT\n",
                "J02151": ">NC_002023.1 wrong stem\nACGT\n",
            },
        )
    assert (out / "V00603.fasta").is_file()
    assert not (out / "J02151.fasta").exists()

    report, second_fetch = _run(
        table,
        out,
        {"J02151": ">J02151.1 influenza\nTTTT\n"},
    )
    assert second_fetch.calls == ["J02151"]
    assert report.cached == (out / "V00603.fasta",)
    assert report.written == (out / "J02151.fasta",)
