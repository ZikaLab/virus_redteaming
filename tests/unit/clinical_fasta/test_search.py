"""Part 1 keeps successful rows and drops cells with no hits."""

from pathlib import Path

import pytest

from virus_redteaming.clinical_fasta.accession_list import AccessionList
from virus_redteaming.clinical_fasta.accession_sink import AtomicAccessionTableSink
from virus_redteaming.clinical_fasta.errors import NcbiSearchMiss
from virus_redteaming.clinical_fasta.length import LengthCutoff
from virus_redteaming.clinical_fasta.search_term import SearchTermAlternatives
from virus_redteaming.clinical_fasta.search_workflow import AccessionSearch
from virus_redteaming.clinical_fasta.term import EntrezTermComposer


class _Viruses:
    def __init__(self, cells: tuple[str, ...]) -> None:
        self._cells = cells

    def read(self) -> tuple[str, ...]:
        return self._cells


class _Extra:
    def __init__(self, text: str = "extra") -> None:
        self._text = text

    def read(self) -> str:
        return self._text


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
        SearchTermAlternatives(),
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
        SearchTermAlternatives(),
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
        SearchTermAlternatives(),
        EntrezTermComposer(),
        _Searcher({"beta": ()}),
        AccessionList(),
        LengthCutoff(),
        AtomicAccessionTableSink(destination),
    )
    with pytest.raises(NcbiSearchMiss):
        empty.run()
    assert destination.read_text(encoding="utf-8") == text


def test_search_retries_the_next_alternative_with_the_length_max(
    tmp_path: Path,
) -> None:
    cutoff = LengthCutoff()
    clause = cutoff.slen_clause()
    assert f":{cutoff.MAX_SLEN}[SLEN]" in clause
    first = f'"Flexal virus" AND complete genome AND {clause}'
    second = f'"Flexal virus" AND complete sequence AND {clause}'
    searcher = _Searcher({second: ("NG_000099.1",)})
    result = AccessionSearch(
        _Viruses(("Flexal virus",)),
        _Extra("complete genome or complete sequence"),
        SearchTermAlternatives(),
        EntrezTermComposer(),
        searcher,
        AccessionList(),
        cutoff,
        AtomicAccessionTableSink(tmp_path / "accessions.csv"),
    ).run()
    assert searcher.terms == [first, second]
    assert " or " not in first
    assert " or " not in second
    assert result.misses == ()
    assert "NG_000099.1" in result.path.read_text(encoding="utf-8")

    stopped = _Searcher({first: ("NG_000099.1",), second: ("OTHER",)})
    AccessionSearch(
        _Viruses(("Flexal virus",)),
        _Extra("complete genome or complete sequence"),
        SearchTermAlternatives(),
        EntrezTermComposer(),
        stopped,
        AccessionList(),
        cutoff,
        AtomicAccessionTableSink(tmp_path / "stopped.csv"),
    ).run()
    assert stopped.terms == [first]


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


def test_run_command_continues_after_a_partial_miss(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from virus_redteaming.clinical_fasta.__main__ import main
    from virus_redteaming.clinical_fasta.models import SearchResult

    order: list[str] = []

    def _fake_search(filename: str, cutoff: LengthCutoff) -> SearchResult:
        order.append(f"search:{filename}:{cutoff.bp}")
        return SearchResult(path=Path("output/accessions.csv"), misses=("beta",))

    def _fake_download(cutoff: LengthCutoff) -> tuple[Path, ...]:
        order.append(f"download:{cutoff.bp}")
        return (Path("output/clinical_genes/NG_000099.1.fasta"),)

    def _fake_parse() -> tuple[Path, Path, Path]:
        order.append("parse")
        return (
            Path("output/accession_criteria.csv"),
            Path("output/NCBI_representative_seq.csv"),
            Path("output/genes.csv"),
        )

    monkeypatch.setattr(
        "virus_redteaming.clinical_fasta.__main__._search",
        _fake_search,
    )
    monkeypatch.setattr(
        "virus_redteaming.clinical_fasta.__main__._download",
        _fake_download,
    )
    monkeypatch.setattr(
        "virus_redteaming.clinical_fasta.__main__._parse",
        _fake_parse,
    )
    assert main(["run", "genes.csv"]) == 1
    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "output/accessions.csv",
        "output/clinical_genes/NG_000099.1.fasta",
        "output/accession_criteria.csv",
        "output/NCBI_representative_seq.csv",
        "output/genes.csv",
    ]
    assert captured.err.strip() == "no accessions for Virus cell: beta"
    assert order == ["search:genes.csv:7000", "download:7000", "parse"]


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
