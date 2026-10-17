"""Entrez client arguments, atomic sinks, and API-key redaction."""

from pathlib import Path

import pytest

from virus_redteaming.clinical_fasta.accession_sink import AtomicAccessionTableSink
from virus_redteaming.clinical_fasta.biopython_entrez import BiopythonEntrezClient
from virus_redteaming.clinical_fasta.config import NcbiEntrezConfig
from virus_redteaming.clinical_fasta.errors import FastaWriteError
from virus_redteaming.clinical_fasta.models import AccessionHit, FastaRecord
from virus_redteaming.clinical_fasta.sink import AtomicPathFastaSink


def test_entrez_client_omits_unset_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[dict[str, object]] = []

    class _Handle:
        def read(self) -> str:
            return ">NG_1\nA\n"

        def close(self) -> None:
            return None

    def esearch(**kwargs: object) -> _Handle:
        seen.append(kwargs)
        return _Handle()

    def efetch(**kwargs: object) -> _Handle:
        seen.append(kwargs)
        return _Handle()

    monkeypatch.setattr(
        "virus_redteaming.clinical_fasta.biopython_entrez.Entrez.esearch",
        esearch,
    )
    monkeypatch.setattr(
        "virus_redteaming.clinical_fasta.biopython_entrez.Entrez.read",
        lambda handle: {"IdList": ["NG_1"]},
    )
    monkeypatch.setattr(
        "virus_redteaming.clinical_fasta.biopython_entrez.Entrez.efetch",
        efetch,
    )
    client = BiopythonEntrezClient(NcbiEntrezConfig(email="person@example.com"))
    client.search("term")
    client.fetch_fasta("NG_1")
    assert all("api_key" not in call for call in seen)

    keyed = BiopythonEntrezClient(
        NcbiEntrezConfig(email="person@example.com", api_key="secret-key")
    )
    keyed.search("term")
    keyed.fetch_fasta("NG_1")
    assert seen[2]["api_key"] == "secret-key"
    assert seen[3]["api_key"] == "secret-key"


def test_sink_replaces_atomically_and_removes_temp_on_failure(tmp_path: Path) -> None:
    destination = tmp_path / "accessions.csv"
    destination.write_text("old\n", encoding="utf-8")
    sink = AtomicAccessionTableSink(destination)
    sink.write([AccessionHit("alpha", 1, "NG_1")])
    assert destination.read_text(encoding="utf-8").startswith("Virus,Rank,Accession")
    assert list(tmp_path.glob("*.tmp")) == []

    class _Broken(AtomicAccessionTableSink):
        def write(self, hits: tuple[AccessionHit, ...] | list[AccessionHit]) -> Path:
            raise FastaWriteError("boom")

    before = destination.read_text(encoding="utf-8")
    with pytest.raises(FastaWriteError):
        _Broken(destination).write([])
    assert destination.read_text(encoding="utf-8") == before

    fasta = AtomicPathFastaSink(tmp_path / "genes")
    written = fasta.write(FastaRecord("NG_1", ">NG_1\nA\n"))
    assert written.read_text(encoding="utf-8") == ">NG_1\nA\n"
    assert list((tmp_path / "genes").glob("*.tmp")) == []


def test_errors_and_logs_redact_api_key() -> None:
    config = NcbiEntrezConfig(email="person@example.com", api_key="secret-key")
    assert "secret-key" not in repr(config)
    assert "secret-key" not in str(config)
