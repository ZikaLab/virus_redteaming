"""Part 1 keeps successful rows and drops cells with no hits."""

from pathlib import Path

import pytest

from virus_redteaming.clinical_fasta.accession_list import AccessionList
from virus_redteaming.clinical_fasta.accession_sink import AtomicAccessionTableSink
from virus_redteaming.clinical_fasta.errors import NcbiSearchMiss
from virus_redteaming.clinical_fasta.length import LengthCutoff
from virus_redteaming.clinical_fasta.search_workflow import AccessionSearch
from virus_redteaming.clinical_fasta.term import EntrezTermComposer


class _Viruses:
    def __init__(self, cells: tuple[str, ...]) -> None:
        self._cells = cells

    def read(self) -> tuple[str, ...]:
        return self._cells


class _Extra:
    def read(self) -> str:
        return "extra"


class _Searcher:
    def __init__(self, responses: dict[str, tuple[str, ...]]) -> None:
        self.responses = responses
        self.terms: list[str] = []

    def search(self, term: str) -> tuple[str, ...]:
        self.terms.append(term)
        for phrase, ids in self.responses.items():
            if phrase in term:
                return ids
        return ()


def test_field_query_keeps_all_five_hits(tmp_path: Path) -> None:
    cell = "human[organism] mitochondrion genome"
    ids = (
        "CM200698.1",
        "OZ567094.1",
        "OZ567093.1",
        "OZ560341.1",
        "OZ561974.1",
    )
    term = '"human"[organism] mitochondrion genome'
    searcher = _Searcher({term: ids})
    result = AccessionSearch(
        _Viruses((cell,)),
        _Extra(),
        EntrezTermComposer(),
        searcher,
        AccessionList(),
        LengthCutoff(),
        AtomicAccessionTableSink(tmp_path / "accessions.csv"),
    ).run()
    assert searcher.terms == [term]
    assert result.misses == ()
    text = result.path.read_text(encoding="utf-8")
    for accession in ids:
        assert accession in text


def test_search_keeps_first_5_in_order() -> None:
    eight = tuple(f"A{index}" for index in range(8))
    assert AccessionList().keep(eight) == eight[:5]
    assert AccessionList().keep(("A1", "A2", "A3")) == ("A1", "A2", "A3")


def test_search_miss_does_not_publish_accession_file(tmp_path: Path) -> None:
    destination = tmp_path / "accessions.csv"
    destination.write_text("keep\n", encoding="utf-8")
    searcher = _Searcher({"alpha": ("NM_1",), "beta": ()})
    workflow = AccessionSearch(
        _Viruses(("alpha", "beta")),
        _Extra(),
        EntrezTermComposer(),
        searcher,
        AccessionList(),
        LengthCutoff(),
        AtomicAccessionTableSink(destination),
    )
    result = workflow.run()
    text = result.path.read_text(encoding="utf-8")
    assert result.misses == ("beta",)
    assert "alpha" in text
    assert "NM_1" in text
    assert "beta" not in text

    empty = AccessionSearch(
        _Viruses(("beta",)),
        _Extra(),
        EntrezTermComposer(),
        _Searcher({"beta": ()}),
        AccessionList(),
        LengthCutoff(),
        AtomicAccessionTableSink(destination),
    )
    with pytest.raises(NcbiSearchMiss):
        empty.run()
    assert destination.read_text(encoding="utf-8") == text


def test_search_command_prints_a_miss_and_exits_1(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from virus_redteaming.clinical_fasta.__main__ import main
    from virus_redteaming.clinical_fasta.models import SearchResult

    def _fake_search(filename: str, cutoff: LengthCutoff) -> SearchResult:
        return SearchResult(path=Path("output/accessions.csv"), misses=("beta",))

    monkeypatch.setattr(
        "virus_redteaming.clinical_fasta.__main__._search",
        _fake_search,
    )
    assert main(["search"]) == 1
    captured = capsys.readouterr()
    assert captured.out.strip() == "output/accessions.csv"
    assert captured.err.strip() == "no accessions for Virus cell: beta"


def test_search_does_not_call_efetch(monkeypatch: pytest.MonkeyPatch) -> None:
    from virus_redteaming.clinical_fasta.biopython_entrez import BiopythonEntrezClient
    from virus_redteaming.clinical_fasta.config import NcbiEntrezConfig

    calls: list[str] = []

    def esearch(**kwargs: object) -> object:
        calls.append("esearch")
        assert kwargs["retmax"] == 5
        assert kwargs["retstart"] == 0
        assert kwargs["idtype"] == "acc"
        assert "api_key" not in kwargs

        class _Handle:
            def close(self) -> None:
                calls.append("close")

        return _Handle()

    def read(handle: object) -> dict[str, list[str]]:
        return {"IdList": ["NG_1"]}

    def efetch(**kwargs: object) -> object:
        calls.append("efetch")
        raise AssertionError("efetch")

    monkeypatch.setattr(
        "virus_redteaming.clinical_fasta.biopython_entrez.Entrez.esearch",
        esearch,
    )
    monkeypatch.setattr(
        "virus_redteaming.clinical_fasta.biopython_entrez.Entrez.read",
        read,
    )
    monkeypatch.setattr(
        "virus_redteaming.clinical_fasta.biopython_entrez.Entrez.efetch",
        efetch,
    )
    client = BiopythonEntrezClient(NcbiEntrezConfig(email="person@example.com"))
    assert client.search("term") == ("NG_1",)
    assert calls == ["esearch", "close"]
