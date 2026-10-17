"""Query path, CSV cells, search.txt, and term composition."""

from pathlib import Path

import pytest

from virus_redteaming.clinical_fasta.csv_source import OutputCsvVirusSource
from virus_redteaming.clinical_fasta.errors import NcbiInputError
from virus_redteaming.clinical_fasta.length import LengthCutoff
from virus_redteaming.clinical_fasta.paths import OutputCsvPath
from virus_redteaming.clinical_fasta.search_term import OutputSearchTermSource
from virus_redteaming.clinical_fasta.term import EntrezTermComposer


def test_csv_path_resolves_under_output(tmp_path: Path) -> None:
    resolved = OutputCsvPath("query.csv").resolve(tmp_path)
    assert resolved == tmp_path / "output" / "query.csv"
    for name in ("../secrets.csv", "/tmp/x.csv", "a/b.csv"):
        with pytest.raises(NcbiInputError):
            OutputCsvPath(name).resolve(tmp_path)


def test_csv_reads_virus_column_in_order(tmp_path: Path) -> None:
    path = tmp_path / "query.csv"
    path.write_text("Virus\nalpha \n\n beta\n", encoding="utf-8")
    assert OutputCsvVirusSource(path).read() == ("alpha", "beta")


def test_csv_rejects_missing_virus_header(tmp_path: Path) -> None:
    path = tmp_path / "query.csv"
    path.write_text("Name\nalpha\n", encoding="utf-8")
    with pytest.raises(NcbiInputError):
        OutputCsvVirusSource(path).read()


def test_csv_rejects_all_blank_virus_cells(tmp_path: Path) -> None:
    path = tmp_path / "query.csv"
    path.write_text("Virus\n\n  \n", encoding="utf-8")
    with pytest.raises(NcbiInputError):
        OutputCsvVirusSource(path).read()


def test_search_txt_reads_the_single_line(tmp_path: Path) -> None:
    path = tmp_path / "search.txt"
    path.write_text("  extra  \n", encoding="utf-8")
    assert OutputSearchTermSource(path).read() == "extra"


def test_search_txt_rejects_empty_and_multiple_terms(tmp_path: Path) -> None:
    empty = tmp_path / "empty.txt"
    empty.write_text("  \n", encoding="utf-8")
    many = tmp_path / "many.txt"
    many.write_text("one\ntwo\n", encoding="utf-8")
    with pytest.raises(NcbiInputError):
        OutputSearchTermSource(empty).read()
    with pytest.raises(NcbiInputError):
        OutputSearchTermSource(many).read()


def test_term_composer_quotes_virus_and_ands_extra() -> None:
    cutoff = LengthCutoff()
    term = EntrezTermComposer().compose("alpha beta", "extra", cutoff)
    assert term == f'"alpha beta" AND extra AND {cutoff.slen_clause()}'
    assert "[Accession]" not in term
    assert "[SLEN]" in term


def test_term_composer_sends_field_query_unquoted() -> None:
    cell = "human[organism] mitochondrion genome"
    term = EntrezTermComposer().compose(cell, "gene", LengthCutoff())
    assert term == '"human"[organism] mitochondrion genome'
    assert '"human[organism]' not in term
    assert "AND gene" not in term


def test_term_composer_rejects_embedded_quotes() -> None:
    with pytest.raises(NcbiInputError):
        EntrezTermComposer().compose('foo"bar', "extra", LengthCutoff())
