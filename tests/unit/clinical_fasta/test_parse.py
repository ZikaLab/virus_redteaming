"""Representative parsing. These tests use local files and do not call NCBI."""

import csv
import os
from pathlib import Path

import pytest

from virus_redteaming.clinical_fasta.accession_source import AccessionHitCsvSource
from virus_redteaming.clinical_fasta.criteria_representatives import (
    CriteriaCsvRepresentativeSource,
    CriteriaRepresentativeFiles,
)
from virus_redteaming.clinical_fasta.criteria_sink import AtomicCriteriaSink
from virus_redteaming.clinical_fasta.errors import FastaWriteError, NcbiInputError
from virus_redteaming.clinical_fasta.fasta_measure import FastaMeasure
from virus_redteaming.clinical_fasta.genes_align import AtomicGenesAligner
from virus_redteaming.clinical_fasta.header_match import HeaderMatch
from virus_redteaming.clinical_fasta.models import (
    AccessionHit,
    ChosenAccession,
    CriteriaRow,
    MeasuredFasta,
)
from virus_redteaming.clinical_fasta.parse_workflow import RepresentativeParse
from virus_redteaming.clinical_fasta.representative_selection import (
    RepresentativeSelection,
)
from virus_redteaming.clinical_fasta.representative_sink import AtomicRepresentativeSink
from virus_redteaming.clinical_fasta.screened_words import ScreenedWords

_HEADER = ("homo", "sapiens", "mitochondrion", "complete", "genome")


def test_screened_words_delete_complete_bracket_tags() -> None:
    words = ScreenedWords().from_query("human[organism] mitochondrion genome")
    assert words == ("human", "mitochondrion", "genome")
    assert "[" not in "".join(words)
    assert "]" not in "".join(words)


def test_screened_words_keep_virus_outside_brackets() -> None:
    assert ScreenedWords().from_query("virus[organism]") == ("virus",)


def test_screened_words_empty_when_only_a_tag_remains() -> None:
    assert ScreenedWords().from_query("[organism]") == ()


def test_header_match_counts_whole_words() -> None:
    matched = HeaderMatch().matched_words(_HEADER, ("mitochondrion", "genome", "human"))
    assert matched == ("mitochondrion", "genome")
    assert HeaderMatch().in_order(_HEADER, ("human",)) is False


def test_in_order_allows_words_between() -> None:
    match = HeaderMatch()
    assert match.in_order(_HEADER, ("mitochondrion", "genome")) is True
    assert match.in_order(_HEADER, ("genome", "mitochondrion")) is False


def test_adjacent_requires_words_next_to_each_other() -> None:
    match = HeaderMatch()
    assert match.adjacent(_HEADER, ("mitochondrion", "genome")) is False
    side_by_side = ("mitochondrion", "genome")
    assert match.adjacent(side_by_side, side_by_side) is True


def test_selection_prefers_in_order_then_adjacent_then_length() -> None:
    selection = RepresentativeSelection()
    in_order = _row(accession="NG_000001.1", rank=2, in_order=True, word_match_count=1)
    higher_count = _row(
        accession="NG_000002.1", rank=1, word_match_count=3, gene_length=100
    )
    assert _winner(selection.choose((higher_count, in_order))) == "NG_000001.1"

    gapped = _row(
        accession="NG_000003.1",
        rank=1,
        in_order=True,
        adjacent=False,
        gene_length=500,
    )
    adjacent = _row(
        accession="NG_000004.1",
        rank=2,
        in_order=True,
        adjacent=True,
        gene_length=10,
    )
    assert _winner(selection.choose((gapped, adjacent))) == "NG_000004.1"

    short = _row(accession="NG_000005.1", rank=1, word_match_count=1, gene_length=10)
    long = _row(accession="NG_000006.1", rank=2, word_match_count=1, gene_length=40_000)
    assert _winner(selection.choose((short, long))) == "NG_000006.1"

    later = _row(accession="NG_000007.1", rank=5, word_match_count=1, gene_length=20)
    earlier = _row(accession="NG_000008.1", rank=2, word_match_count=1, gene_length=20)
    assert _winner(selection.choose((later, earlier))) == "NG_000008.1"


def test_selection_rejects_length_above_40000(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">insulin\n" + ("A" * 40_000))
    _write_fasta(tmp_path, "NG_000002.1", ">insulin\n" + ("A" * 40_001))
    criteria, _, _ = _run(
        tmp_path,
        [("insulin", 1, "NG_000001.1"), ("insulin", 2, "NG_000002.1")],
        "Virus\ninsulin\n",
    )
    rows = _criteria(criteria)
    assert rows[0]["Representative"] == "1"
    assert rows[0]["GeneLength"] == "40000"
    assert rows[0]["WithinUpperCutoff"] == "1"
    assert rows[1]["Failure"] == "longer than 40000 bp"
    assert rows[1]["Representative"] == "0"
    assert rows[1]["WithinUpperCutoff"] == "0"


def test_missing_fasta_is_a_criteria_failure(tmp_path: Path) -> None:
    criteria, _, _ = _run(tmp_path, [("insulin", 1, "NG_000001.1")], "Virus\ninsulin\n")
    row = _criteria(criteria)[0]
    assert row["Failure"] == "missing fasta"
    assert row["GeneLength"] == ""
    assert row["Header"] == ""
    assert row["MatchContinuationPenalty"] == ""
    assert row["Representative"] == "0"


def test_no_screened_words_fails_every_row(tmp_path: Path) -> None:
    criteria, representative, _ = _run(
        tmp_path, [("[organism]", 1, "NG_000001.1")], "Virus\n[organism]\n"
    )
    row = _criteria(criteria)[0]
    assert row["Failure"] == "no screened words"
    assert row["Representative"] == "0"
    assert _plain(representative) == [
        ["Query", "Accession", "GeneLength", "Sequence", "Representative"]
    ]


def test_no_word_match_is_reported(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">zzzz\nAC\n")
    criteria, _, _ = _run(tmp_path, [("insulin", 1, "NG_000001.1")], "Virus\ninsulin\n")
    assert _criteria(criteria)[0]["Failure"] == "no word match"
    assert _criteria(criteria)[0]["MatchContinuationPenalty"] == "0"


def test_criteria_escapes_commas_and_keeps_representative_last(tmp_path: Path) -> None:
    destination = tmp_path / "accession_criteria.csv"
    AtomicCriteriaSink(destination).write((_row(query="a,b", header="x,y"),))
    text = destination.read_text(encoding="utf-8")
    assert "a\\,b" in text
    assert '"a,b"' not in text
    rows = _criteria(destination)
    assert list(rows[0])[-1] == "Representative"
    assert rows[0]["Query"] == "a,b"
    assert rows[0]["Header"] == "x,y"


def test_accession_hit_source_keeps_rank_and_repeats(tmp_path: Path) -> None:
    path = tmp_path / "accessions.csv"
    path.write_text(
        "Virus,Rank,Accession\n"
        "insulin,1,NG_000001.1\n"
        "mt,1,NC_012920.1\n"
        "insulin,2,NG_000002.1\n",
        encoding="utf-8",
    )
    hits = AccessionHitCsvSource(path).read()
    assert [(hit.virus, hit.rank, hit.accession) for hit in hits] == [
        ("insulin", 1, "NG_000001.1"),
        ("mt", 1, "NC_012920.1"),
        ("insulin", 2, "NG_000002.1"),
    ]
    missing = tmp_path / "missing.csv"
    missing.write_text("Rank,Accession\n1,NG_000001.1\n", encoding="utf-8")
    with pytest.raises(NcbiInputError):
        AccessionHitCsvSource(missing).read()
    broken = tmp_path / "rank.csv"
    broken.write_text(
        "Virus,Rank,Accession\ninsulin,no,NG_000001.1\n",
        encoding="utf-8",
    )
    with pytest.raises(NcbiInputError):
        AccessionHitCsvSource(broken).read()


def test_criteria_reader_uses_the_escape_once(tmp_path: Path) -> None:
    destination = tmp_path / "accession_criteria.csv"
    AtomicCriteriaSink(destination).write((_row(query="a,b", representative=True),))
    text = destination.read_text(encoding="utf-8")
    assert "a\\,b" in text
    assert "a\\\\,b" not in text
    assert CriteriaCsvRepresentativeSource(destination).read()[0].query == "a,b"


def test_two_winners_for_one_query_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "accession_criteria.csv"
    path.write_text(
        "Query,Accession,Representative\n"
        "insulin,NG_000001.1,1\n"
        "insulin,NG_000002.1,1\n",
        encoding="utf-8",
    )
    with pytest.raises(NcbiInputError):
        CriteriaCsvRepresentativeSource(path).read()


def test_genes_csv_matches_a_query_with_a_comma(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">a b\nAC\n")
    _, _, genes = _run(tmp_path, [("a,b", 1, "NG_000001.1")], 'Virus\n"a,b"\n')
    criteria = tmp_path / "output" / "accession_criteria.csv"
    assert "a\\,b" in criteria.read_text(encoding="utf-8")
    assert '"a,b"' in genes.read_text(encoding="utf-8")
    assert _plain(genes)[1][1] == "NG_000001.1"


def test_overlong_fasta_keeps_match_fields(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">insulin gene\n" + ("A" * 40_001))
    criteria, _, _ = _run(tmp_path, [("insulin", 1, "NG_000001.1")], "Virus\ninsulin\n")
    row = _criteria(criteria)[0]
    assert row["Failure"] == "longer than 40000 bp"
    assert row["Header"] == "insulin gene"
    assert row["InOrderMatch"] == "1"
    assert row["WordMatchCount"] == "1"
    assert row["WithinUpperCutoff"] == "0"


def test_no_screened_words_still_measures_a_present_fasta(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">insulin gene\nACGT\n")
    criteria, _, _ = _run(
        tmp_path,
        [("[organism]", 1, "NG_000001.1")],
        "Virus\n[organism]\n",
    )
    row = _criteria(criteria)[0]
    assert row["Failure"] == "no screened words"
    assert row["GeneLength"] == "4"
    assert row["Header"] == "insulin gene"
    assert row["InOrderMatch"] == "0"
    assert row["AdjacentMatch"] == "0"
    assert row["WordMatchCount"] == "0"
    assert row["MatchContinuationPenalty"] == "0"


def test_parse_groups_a_repeated_virus_cell(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">insulin\nAA\n")
    _write_fasta(tmp_path, "NG_000002.1", ">insulin\nAAAA\n")
    _write_fasta(tmp_path, "NC_012920.1", ">mitochondrion genome\nA\n")
    criteria, representative, _ = _run(
        tmp_path,
        [
            ("insulin", 1, "NG_000001.1"),
            ("mitochondrion genome", 1, "NC_012920.1"),
            ("insulin", 2, "NG_000002.1"),
        ],
        "Virus\ninsulin\nmitochondrion genome\n",
    )
    rows = _criteria(criteria)
    assert [row["Accession"] for row in rows] == [
        "NG_000001.1",
        "NC_012920.1",
        "NG_000002.1",
    ]
    insulin = [row for row in rows if row["Query"] == "insulin"]
    assert [row["Representative"] for row in insulin] == ["0", "1"]
    assert [row[1] for row in _plain(representative)[1:]] == [
        "NG_000002.1",
        "NC_012920.1",
    ]


def test_parse_command_does_not_require_min_length(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">insulin\nAC\n")
    _accessions(tmp_path, [("insulin", 1, "NG_000001.1")])
    (tmp_path / "output" / "genes.csv").write_text("Virus\ninsulin\n", encoding="utf-8")

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("parse called NCBI")

    monkeypatch.setattr(
        "virus_redteaming.clinical_fasta.__main__.BiopythonEntrezClient",
        refuse,
    )
    monkeypatch.chdir(tmp_path)
    from virus_redteaming.clinical_fasta.__main__ import main

    assert main(["parse"]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert [Path(line).name for line in printed] == [
        "accession_criteria.csv",
        "NCBI_representative_seq.csv",
        "genes.csv",
    ]


def test_parse_rejects_a_missing_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    from virus_redteaming.clinical_fasta.__main__ import main

    assert main(["parse"]) == 1
    assert "missing" in capsys.readouterr().err
    output = tmp_path / "output"
    output.mkdir()
    (output / "accessions.csv").write_text(
        "Rank,Accession\n1,NG_000001.1\n",
        encoding="utf-8",
    )
    assert main(["parse"]) == 1
    assert "header" in capsys.readouterr().err


def test_accession_hit_source_rejects_bad_ranks_and_ids(tmp_path: Path) -> None:
    cases = [
        "Virus,Rank,Accession\ninsulin,6,NG_000001.1\n",
        "Virus,Rank,Accession\ninsulin,1,NG_000001.1\ninsulin,1,NG_000002.1\n",
        "Virus,Rank,Accession\n"
        "insulin,1,NG_000001.1\ninsulin,2,NG_000002.1\ninsulin,3,NG_000003.1\n"
        "insulin,4,NG_000004.1\ninsulin,5,NG_000005.1\ninsulin,1,NG_000006.1\n",
        "Virus,Rank,Accession\n,1,NG_000001.1\n",
        "Virus,Rank,Accession\ninsulin,1,not-an-id\n",
    ]
    for index, text in enumerate(cases):
        path = tmp_path / f"bad-{index}.csv"
        path.write_text(text, encoding="utf-8")
        with pytest.raises(NcbiInputError):
            AccessionHitCsvSource(path).read()


def test_fasta_measure_rejects_a_bad_file(tmp_path: Path) -> None:
    measure = FastaMeasure()
    empty = tmp_path / "empty.fasta"
    empty.write_text("", encoding="utf-8")
    plain = tmp_path / "plain.fasta"
    plain.write_text("ACGT\n", encoding="utf-8")
    doubled = tmp_path / "two.fasta"
    doubled.write_text(">one\nAC\n>two\nGT\n", encoding="utf-8")
    for path in (empty, plain, doubled):
        with pytest.raises(NcbiInputError):
            measure.read(path)
    assert measure.read(tmp_path / "absent.fasta") is None


def test_criteria_reader_rejects_a_bad_table(tmp_path: Path) -> None:
    missing_header = tmp_path / "header.csv"
    missing_header.write_text("Foo,Bar\n1,2\n", encoding="utf-8")
    bad_flag = tmp_path / "flag.csv"
    bad_flag.write_text(
        "Query,Accession,Representative\ninsulin,NG_000001.1,2\n",
        encoding="utf-8",
    )
    blank = tmp_path / "blank.csv"
    blank.write_text(
        "Query,Accession,Representative\n,NG_000001.1,1\n",
        encoding="utf-8",
    )
    for path in (missing_header, bad_flag, blank):
        with pytest.raises(NcbiInputError):
            CriteriaCsvRepresentativeSource(path).read()
    absent = tmp_path / "absent.csv"
    with pytest.raises(NcbiInputError):
        CriteriaCsvRepresentativeSource(absent).read()


def test_representative_and_genes_use_ordinary_csv_quotes(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">a b\nAC\n")
    _, representative, genes = _run(
        tmp_path, [("a,b", 1, "NG_000001.1")], 'Virus\n"a,b"\n'
    )
    representative_text = representative.read_text(encoding="utf-8")
    genes_text = genes.read_text(encoding="utf-8")
    assert '"a,b"' in representative_text
    assert "\\," not in representative_text
    assert '"a,b"' in genes_text
    assert "\\," not in genes_text


def test_criteria_and_representative_sinks_replace_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    criteria = tmp_path / "accession_criteria.csv"
    representative = tmp_path / "NCBI_representative_seq.csv"
    criteria.write_text("old-criteria\n", encoding="utf-8")
    representative.write_text("old-representative\n", encoding="utf-8")

    def refuse(_source: Path, _destination: Path) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(
        "virus_redteaming.clinical_fasta.atomic_replace.os.replace",
        refuse,
    )
    with pytest.raises(FastaWriteError):
        AtomicCriteriaSink(criteria).write((_row(),))
    with pytest.raises(FastaWriteError):
        AtomicRepresentativeSink(representative).write((_row(representative=True),))
    assert criteria.read_text(encoding="utf-8") == "old-criteria\n"
    assert representative.read_text(encoding="utf-8") == "old-representative\n"
    assert list(tmp_path.glob("*.tmp")) == []


def test_representative_file_contains_only_chosen_sequences(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">insulin\nACGT\n")
    _write_fasta(tmp_path, "NC_012920.1", ">other gene\nAA\n")
    _, representative, _ = _run(
        tmp_path,
        [("insulin", 1, "NG_000001.1"), ("zzzz", 1, "NC_012920.1")],
        "Virus\ninsulin\nzzzz\n",
    )
    rows = _plain(representative)
    assert rows[0] == ["Query", "Accession", "GeneLength", "Sequence", "Representative"]
    assert rows[1:] == [["insulin", "NG_000001.1", "4", "ACGT", "1"]]


def test_genes_csv_adds_accession_once(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">insulin\nAC\n")
    _, _, genes = _run(
        tmp_path,
        [("insulin", 1, "NG_000001.1")],
        "Virus,Note\ninsulin,x\n",
    )
    _run(tmp_path, [("insulin", 1, "NG_000001.1")], genes.read_text(encoding="utf-8"))
    header = _plain(genes)[0]
    assert header[-1] == "Accession"
    assert header.count("Accession") == 1
    assert _plain(genes)[1][-1] == "NG_000001.1"


def test_genes_csv_repeats_one_accession_for_duplicate_virus_text(
    tmp_path: Path,
) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">insulin\nAC\n")
    _, _, genes = _run(
        tmp_path,
        [("insulin", 1, "NG_000001.1")],
        "Virus,Note\ninsulin,one\ninsulin,two\n",
    )
    body = _plain(genes)[1:]
    assert [row[-1] for row in body] == ["NG_000001.1", "NG_000001.1"]


def test_genes_csv_match_trims_ends_only(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">human insulin\nAC\n")
    _, _, genes = _run(
        tmp_path,
        [("human insulin", 1, "NG_000001.1")],
        "Virus\n human insulin \nHuman insulin\n",
    )
    assert [row[-1] for row in _plain(genes)[1:]] == ["NG_000001.1", ""]


def test_genes_csv_replace_is_atomic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    genes = tmp_path / "genes.csv"
    genes.write_text("Virus\ninsulin\n", encoding="utf-8")

    def refuse(_source: Path, _destination: Path) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(
        "virus_redteaming.clinical_fasta.atomic_replace.os.replace",
        refuse,
    )
    with pytest.raises(FastaWriteError):
        AtomicGenesAligner(genes).write(())
    assert genes.read_text(encoding="utf-8") == "Virus\ninsulin\n"
    assert list(tmp_path.glob("*.tmp")) == []


def test_screened_words_keep_first_seen_order() -> None:
    words = ScreenedWords().from_query("Insulin insulin gene gene")
    assert words == ("insulin", "gene")


def test_worked_header_matches_mitochondrion_and_genome(tmp_path: Path) -> None:
    header = "OZ567094.1 Homo sapiens genome assembly, organelle: mitochondrion"
    _write_fasta(tmp_path, "NG_000001.1", f">{header}\nAC\n")
    criteria, representative, _ = _run(
        tmp_path,
        [("human[organism] mitochondrion genome", 1, "NG_000001.1")],
        "Virus\nhuman[organism] mitochondrion genome\n",
    )
    row = _criteria(criteria)[0]
    assert row["Query"] == "human[organism] mitochondrion genome"
    assert row["ScreenedWords"] == "human;mitochondrion;genome"
    assert row["MatchedWords"] == "mitochondrion;genome"
    assert row["WordMatchCount"] == "2"
    assert row["InOrderMatch"] == "0"
    assert row["AdjacentMatch"] == "0"
    assert "human" not in row["MatchedWords"].split(";")
    assert row["Header"] == header
    assert row["GeneLength"] == "2"
    assert row["WithinUpperCutoff"] == "1"
    assert row["Failure"] == ""
    assert row["Representative"] == "1"
    assert list(row)[-1] == "Representative"
    text = criteria.read_text(encoding="utf-8")
    assert "assembly\\, organelle" in text
    assert '"assembly, organelle"' not in text
    sequence = _plain(representative)[1][3]
    assert sequence == "AC"
    assert not sequence.startswith(">")


def test_gene_length_ignores_the_header_and_whitespace(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">insulin gene\nAC GT\n\n")
    criteria, representative, _ = _run(
        tmp_path,
        [("insulin", 1, "NG_000001.1")],
        "Virus\ninsulin\n",
    )
    row = _criteria(criteria)[0]
    assert row["GeneLength"] == "4"
    assert row["Header"] == "insulin gene"
    assert _plain(representative)[1][3] == "ACGT"


def test_eligible_loser_keeps_an_empty_failure(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">insulin\nAA\n")
    _write_fasta(tmp_path, "NG_000002.1", ">insulin\nAAAA\n")
    criteria, _, _ = _run(
        tmp_path,
        [("insulin", 1, "NG_000001.1"), ("insulin", 2, "NG_000002.1")],
        "Virus\ninsulin\n",
    )
    rows = _criteria(criteria)
    assert rows[0]["Failure"] == ""
    assert rows[0]["Representative"] == "0"
    assert rows[1]["Failure"] == ""
    assert rows[1]["Representative"] == "1"


def test_no_winner_leaves_the_genes_accession_blank(tmp_path: Path) -> None:
    _, _, genes = _run(
        tmp_path,
        [("[organism]", 1, "NG_000001.1")],
        "Family,Virus\nclinical,[organism]\n",
    )
    assert _plain(genes) == [
        ["Family", "Virus", "Accession"],
        ["clinical", "[organism]", ""],
    ]


def test_backslash_is_escaped_once(tmp_path: Path) -> None:
    destination = tmp_path / "accession_criteria.csv"
    AtomicCriteriaSink(destination).write((_row(query="a\\b", representative=True),))
    text = destination.read_text(encoding="utf-8")
    assert "a\\\\b" in text
    assert "a\\\\\\\\b" not in text
    chosen = CriteriaCsvRepresentativeSource(destination).read()
    assert chosen[0].query == "a\\b"


def test_same_accession_winners_collapse_to_one(tmp_path: Path) -> None:
    path = tmp_path / "accession_criteria.csv"
    path.write_text(
        "Query,Accession,Representative\n"
        " insulin ,NG_000001.1,1\n"
        "insulin,NG_000001.1,1\n",
        encoding="utf-8",
    )
    assert CriteriaCsvRepresentativeSource(path).read() == (
        ChosenAccession(query="insulin", accession="NG_000001.1"),
    )


def test_bad_fasta_is_an_input_error(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", "")
    with pytest.raises(NcbiInputError):
        _run(tmp_path, [("insulin", 1, "NG_000001.1")], "Virus\ninsulin\n")
    assert not (tmp_path / "output" / "accession_criteria.csv").exists()


def test_parse_scores_through_injected_fakes(tmp_path: Path) -> None:
    hits = (
        AccessionHit(virus="insulin", rank=1, accession="NG_000001.1"),
        AccessionHit(virus="insulin", rank=2, accession="NG_000002.1"),
    )
    measure = _FakeMeasure()
    criteria = _FakeCriteriaSink()
    representative = _FakeRepresentativeSink()
    opener = _FakeOpener()
    genes = _FakeGenes()
    workflow = RepresentativeParse(
        group_source=_FakeGroups(hits),
        fasta_directory=tmp_path / "clinical_genes",
        screened_words=ScreenedWords(),
        measure=measure,
        match=HeaderMatch(),
        selection=RepresentativeSelection(),
        criteria_sink=criteria,
        representative_sink=representative,
        representative_source=opener,
        genes_aligner=genes,
    )
    workflow.run()
    assert [path.name for path in measure.paths] == [
        "NG_000001.1.fasta",
        "NG_000002.1.fasta",
    ]
    assert [row.accession for row in criteria.rows] == ["NG_000001.1", "NG_000002.1"]
    assert [row.accession for row in representative.rows] == ["NG_000002.1"]
    assert opener.path == criteria.path
    assert genes.chosen == (ChosenAccession(query="insulin", accession="FROM-READER"),)


def test_screened_words_delete_every_complete_tag() -> None:
    words = ScreenedWords().from_query(
        "human[organism] mitochondrion[title] genome[SLEN]"
    )
    assert words == ("human", "mitochondrion", "genome")


def test_header_match_is_case_insensitive(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">Insulin\nAC\n")
    criteria, _, _ = _run(tmp_path, [("insulin", 1, "NG_000001.1")], "Virus\ninsulin\n")
    row = _criteria(criteria)[0]
    assert row["InOrderMatch"] == "1"
    assert row["Representative"] == "1"


def test_header_match_rejects_a_longer_word(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">humans\nAC\n")
    _write_fasta(tmp_path, "NG_000002.1", ">human\nAA\n")
    criteria, _, _ = _run(
        tmp_path,
        [("human", 1, "NG_000001.1"), ("human", 2, "NG_000002.1")],
        "Virus\nhuman\n",
    )
    rows = _criteria(criteria)
    assert rows[0]["Failure"] == "no word match"
    assert rows[1]["Representative"] == "1"


def test_in_order_beats_the_same_words_reversed(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">genome mitochondrion\n" + ("A" * 20))
    _write_fasta(tmp_path, "NG_000002.1", ">mitochondrion complete genome\nAAAA\n")
    criteria, _, _ = _run(
        tmp_path,
        [
            ("mitochondrion genome", 1, "NG_000001.1"),
            ("mitochondrion genome", 2, "NG_000002.1"),
        ],
        "Virus\nmitochondrion genome\n",
    )
    rows = _criteria(criteria)
    assert rows[0]["InOrderMatch"] == "0"
    assert rows[0]["Failure"] == ""
    assert rows[0]["Representative"] == "0"
    assert rows[1]["InOrderMatch"] == "1"
    assert rows[1]["AdjacentMatch"] == "0"
    assert rows[1]["Representative"] == "1"


def test_adjacent_beats_a_longer_gapped_match(tmp_path: Path) -> None:
    _write_fasta(
        tmp_path,
        "NG_000001.1",
        ">mitochondrion complete genome\n" + ("A" * 20),
    )
    _write_fasta(tmp_path, "NG_000002.1", ">mitochondrion genome\nAAAA\n")
    criteria, _, _ = _run(
        tmp_path,
        [
            ("mitochondrion genome", 1, "NG_000001.1"),
            ("mitochondrion genome", 2, "NG_000002.1"),
        ],
        "Virus\nmitochondrion genome\n",
    )
    rows = _criteria(criteria)
    assert rows[0]["InOrderMatch"] == "1"
    assert rows[0]["AdjacentMatch"] == "0"
    assert rows[0]["Representative"] == "0"
    assert rows[1]["AdjacentMatch"] == "1"
    assert rows[1]["Representative"] == "1"


def test_equal_fasta_length_keeps_the_lower_rank(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">insulin\nACGT\n")
    _write_fasta(tmp_path, "NG_000002.1", ">insulin\nACGT\n")
    criteria, _, _ = _run(
        tmp_path,
        [("insulin", 1, "NG_000001.1"), ("insulin", 2, "NG_000002.1")],
        "Virus\ninsulin\n",
    )
    rows = _criteria(criteria)
    assert rows[0]["Representative"] == "1"
    assert rows[1]["Representative"] == "0"
    assert rows[1]["Failure"] == ""


def test_overlong_with_no_match_reports_length_first(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">zzzz\n" + ("A" * 40_001))
    criteria, _, _ = _run(tmp_path, [("insulin", 1, "NG_000001.1")], "Virus\ninsulin\n")
    row = _criteria(criteria)[0]
    assert row["Failure"] == "longer than 40000 bp"
    assert row["WordMatchCount"] == "0"


def test_overlong_in_order_loses_to_a_shorter_partial_match(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">human insulin\n" + ("A" * 40_001))
    _write_fasta(tmp_path, "NG_000002.1", ">insulin\n" + ("A" * 10))
    criteria, _, _ = _run(
        tmp_path,
        [("human insulin", 1, "NG_000001.1"), ("human insulin", 2, "NG_000002.1")],
        "Virus\nhuman insulin\n",
    )
    rows = _criteria(criteria)
    assert rows[0]["Failure"] == "longer than 40000 bp"
    assert rows[0]["InOrderMatch"] == "1"
    assert rows[0]["Representative"] == "0"
    assert rows[1]["Failure"] == ""
    assert rows[1]["WordMatchCount"] == "1"
    assert rows[1]["Representative"] == "1"


def test_ordinary_csv_doubles_an_internal_quote(tmp_path: Path) -> None:
    genes = tmp_path / "genes.csv"
    with genes.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Virus"])
        writer.writerow(['say "hi"'])
    AtomicGenesAligner(genes).write(
        (ChosenAccession(query='say "hi"', accession="NG_000001.1"),)
    )
    representative = tmp_path / "NCBI_representative_seq.csv"
    AtomicRepresentativeSink(representative).write(
        (_row(query='say "hi"', representative=True),)
    )
    genes_text = genes.read_text(encoding="utf-8")
    representative_text = representative.read_text(encoding="utf-8")
    assert 'say ""hi""' in genes_text
    assert 'say ""hi""' in representative_text
    assert "\\," not in genes_text
    assert "\\," not in representative_text


def test_genes_csv_updates_an_accession_column_in_place(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">insulin\nAA\n")
    _write_fasta(tmp_path, "NG_000002.1", ">insulin\nAAAA\n")
    hits = [("insulin", 1, "NG_000001.1"), ("insulin", 2, "NG_000002.1")]
    _, _, genes = _run(
        tmp_path,
        hits,
        "Family,Virus,Accession,Note\nalpha,insulin,STALE,keep\n",
    )
    assert _plain(genes) == [
        ["Family", "Virus", "Accession", "Note"],
        ["alpha", "insulin", "NG_000002.1", "keep"],
    ]
    _write_fasta(tmp_path, "NG_000002.1", ">zzzz\nAAAA\n")
    _, _, genes = _run(tmp_path, hits, genes.read_text(encoding="utf-8"))
    assert _plain(genes) == [
        ["Family", "Virus", "Accession", "Note"],
        ["alpha", "insulin", "NG_000001.1", "keep"],
    ]


def test_later_write_failure_keeps_the_earlier_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">insulin\nAC\n")
    output = _accessions(tmp_path, [("insulin", 1, "NG_000001.1")])
    genes = output / "genes.csv"
    original = "Virus\ninsulin\n"
    genes.write_text(original, encoding="utf-8")
    real_replace = os.replace

    def refuse(source: str, destination: str) -> None:
        if Path(destination).name == "genes.csv":
            raise OSError("replace failed")
        real_replace(source, destination)

    monkeypatch.setattr(
        "virus_redteaming.clinical_fasta.atomic_replace.os.replace",
        refuse,
    )
    with pytest.raises(FastaWriteError):
        _workflow(output).run()
    criteria = (output / "accession_criteria.csv").read_text(encoding="utf-8")
    representative_path = output / "NCBI_representative_seq.csv"
    representative = representative_path.read_text(encoding="utf-8")
    assert "NG_000001.1" in criteria
    assert "NG_000001.1" in representative
    assert genes.read_text(encoding="utf-8") == original
    assert list(output.glob("*.tmp")) == []


def test_missing_genes_csv_leaves_the_earlier_tables(tmp_path: Path) -> None:
    _write_fasta(tmp_path, "NG_000001.1", ">insulin\nAC\n")
    output = _accessions(tmp_path, [("insulin", 1, "NG_000001.1")])
    with pytest.raises(NcbiInputError):
        _workflow(output).run()
    assert (output / "accession_criteria.csv").is_file()
    assert (output / "NCBI_representative_seq.csv").is_file()
    assert not (output / "genes.csv").exists()


def test_parse_command_rejects_min_length() -> None:
    from virus_redteaming.clinical_fasta.__main__ import main

    with pytest.raises(SystemExit) as caught:
        main(["parse", "--min-length", "10"])
    assert caught.value.code == 2


def test_continuation_penalty_measures_each_worked_header() -> None:
    match = HeaderMatch()
    examples = (
        ("insulin (INS)", ("insulin",), 0),
        ("insulin receptor (INSR)", ("insulin",), 1),
        ("insulin like growth factor 2 (IGF2)", ("insulin",), 4),
        (
            "genome assembly, organelle: mitochondrion",
            ("genome", "mitochondrion"),
            1,
        ),
        (
            "mitochondrion, complete sequence, whole genome shotgun sequence",
            ("mitochondrion", "genome"),
            2,
        ),
    )
    for header, words, penalty in examples:
        assert match.continuation_penalty(header, words) == penalty


def test_continuation_penalty_stops_at_each_boundary() -> None:
    match = HeaderMatch()
    for boundary in ",;:()[]/":
        header = f"alpha beta{boundary}gamma"
        assert match.continuation_penalty(header, ("alpha",)) == 1
    assert match.continuation_penalty("alpha beta gamma", ("alpha",)) == 2


def test_continuation_penalty_keeps_the_nearest_repeat() -> None:
    penalty = HeaderMatch().continuation_penalty(
        "alpha beta, alpha gamma delta",
        ("alpha",),
    )
    assert penalty == 1
    assert HeaderMatch().continuation_penalty("Alpha (SYM)", ("alpha",)) == 0
    assert HeaderMatch().continuation_penalty("zzzz", ()) == 0
    assert HeaderMatch().continuation_penalty("humans", ("human",)) == 0


def test_selection_uses_continuation_penalty_before_length() -> None:
    exact = _row(
        accession="NG_000001.1",
        rank=2,
        word_match_count=1,
        match_continuation_penalty=0,
        gene_length=10,
    )
    compound = _row(
        accession="NG_000002.1",
        rank=1,
        word_match_count=1,
        match_continuation_penalty=4,
        gene_length=100,
    )
    assert _winner(RepresentativeSelection().choose((compound, exact))) == "NG_000001.1"


def test_parse_chooses_the_exact_insulin_label(tmp_path: Path) -> None:
    _plant(
        tmp_path,
        "NM_001079817.3",
        "Homo sapiens insulin receptor (INSR), transcript variant 2, mRNA",
        "A" * 10,
    )
    _plant(
        tmp_path,
        "NG_008852.2",
        "Homo sapiens insulin receptor (INSR), RefSeqGene on chromosome 19",
        "A" * 40_001,
    )
    _plant(
        tmp_path,
        "NG_008849.1",
        "Homo sapiens insulin like growth factor 2 (IGF2), "
        "RefSeqGene (LRG_1031) on chromosome 11",
        "A" * 100,
    )
    _plant(
        tmp_path,
        "NG_007114.1",
        "Homo sapiens insulin (INS), RefSeqGene on chromosome 11",
        "ACGT",
    )
    _plant(
        tmp_path,
        "NC_001144.5",
        "Saccharomyces cerevisiae S288C chromosome XII, complete sequence",
        "A" * 40_001,
    )
    criteria, representative, _ = _run(
        tmp_path,
        [
            ("human insulin", 1, "NM_001079817.3"),
            ("human insulin", 2, "NG_008852.2"),
            ("human insulin", 3, "NG_008849.1"),
            ("human insulin", 4, "NG_007114.1"),
            ("human insulin", 5, "NC_001144.5"),
        ],
        "Virus\nhuman insulin\n",
    )
    rows = {row["Accession"]: row for row in _criteria(criteria)}
    assert rows["NG_007114.1"]["Representative"] == "1"
    assert rows["NG_007114.1"]["MatchContinuationPenalty"] == "0"
    assert rows["NM_001079817.3"]["MatchContinuationPenalty"] == "1"
    assert rows["NG_008849.1"]["MatchContinuationPenalty"] == "4"
    assert rows["NG_008849.1"]["Representative"] == "0"
    assert _plain(representative)[1][1] == "NG_007114.1"


def test_parse_keeps_the_longest_tied_mitochondrion_header(tmp_path: Path) -> None:
    shotgun = (
        "Homo sapiens isolate 37772 mitochondrion, complete sequence, "
        "whole genome shotgun sequence"
    )
    assembly = "Homo sapiens genome assembly, organelle: mitochondrion"
    _plant(tmp_path, "CM200698.1", shotgun, "A" * 100)
    _plant(tmp_path, "OZ567094.1", assembly, "A" * 10)
    _plant(tmp_path, "OZ567093.1", assembly, "A" * 10)
    _plant(tmp_path, "OZ560341.1", assembly, "A" * 80)
    _plant(tmp_path, "OZ561974.1", assembly, "A" * 10)
    criteria, representative, _ = _run(
        tmp_path,
        [
            ("human[organism] mitochondrion genome", 1, "CM200698.1"),
            ("human[organism] mitochondrion genome", 2, "OZ567094.1"),
            ("human[organism] mitochondrion genome", 3, "OZ567093.1"),
            ("human[organism] mitochondrion genome", 4, "OZ560341.1"),
            ("human[organism] mitochondrion genome", 5, "OZ561974.1"),
        ],
        "Virus\nhuman[organism] mitochondrion genome\n",
    )
    chosen = [row for row in _criteria(criteria) if row["Representative"] == "1"]
    assert [row["Accession"] for row in chosen] == ["OZ560341.1"]
    assert _plain(representative)[1][1] == "OZ560341.1"


def _row(**overrides: object) -> CriteriaRow:
    values: dict[str, object] = {
        "query": "insulin",
        "rank": 1,
        "accession": "NG_000001.1",
        "screened_words": ("insulin",),
        "in_order": False,
        "adjacent": False,
        "word_match_count": 0,
        "matched_words": (),
        "match_continuation_penalty": 0,
        "gene_length": 4,
        "within_cutoff": True,
        "header": "insulin",
        "failure": "",
        "representative": False,
        "sequence": "ACGT",
    }
    values.update(overrides)
    return CriteriaRow(**values)  # type: ignore[arg-type]


def _winner(rows: tuple[CriteriaRow, ...]) -> str:
    chosen = [row.accession for row in rows if row.representative]
    assert len(chosen) == 1
    return chosen[0]


def _run(
    tmp_path: Path,
    hits: list[tuple[str, int, str]],
    genes_text: str,
) -> tuple[Path, Path, Path]:
    output = _accessions(tmp_path, hits)
    (output / "genes.csv").write_text(genes_text, encoding="utf-8")
    return _workflow(output).run()


def _workflow(output: Path) -> RepresentativeParse:
    return RepresentativeParse(
        group_source=AccessionHitCsvSource(output / "accessions.csv"),
        fasta_directory=output / "clinical_genes",
        screened_words=ScreenedWords(),
        measure=FastaMeasure(),
        match=HeaderMatch(),
        selection=RepresentativeSelection(),
        criteria_sink=AtomicCriteriaSink(output / "accession_criteria.csv"),
        representative_sink=AtomicRepresentativeSink(
            output / "NCBI_representative_seq.csv"
        ),
        representative_source=CriteriaRepresentativeFiles(),
        genes_aligner=AtomicGenesAligner(output / "genes.csv"),
    )


def _accessions(tmp_path: Path, hits: list[tuple[str, int, str]]) -> Path:
    output = tmp_path / "output"
    (output / "clinical_genes").mkdir(parents=True, exist_ok=True)
    lines = ["Virus,Rank,Accession"]
    for virus, rank, accession in hits:
        lines.append(",".join((_csv_cell(virus), str(rank), accession)))
    (output / "accessions.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def _csv_cell(value: str) -> str:
    if "," in value or '"' in value:
        return '"' + value.replace('"', '""') + '"'
    return value


def _write_fasta(tmp_path: Path, accession: str, text: str) -> None:
    directory = tmp_path / "output" / "clinical_genes"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{accession}.fasta").write_text(text, encoding="utf-8")


def _plant(tmp_path: Path, accession: str, title: str, sequence: str) -> None:
    _write_fasta(tmp_path, accession, f">{accession} {title}\n{sequence}\n")


def _criteria(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(
            handle,
            quoting=csv.QUOTE_NONE,
            escapechar="\\",
            doublequote=False,
        )
        rows = list(reader)
    header = rows[0]
    return [dict(zip(header, row, strict=True)) for row in rows[1:]]


def _plain(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.reader(handle))


class _FakeGroups:
    def __init__(self, hits: tuple[AccessionHit, ...]) -> None:
        self._hits = hits

    def read(self) -> tuple[AccessionHit, ...]:
        return self._hits


class _FakeMeasure:
    def __init__(self) -> None:
        self.paths: list[Path] = []

    def read(self, path: Path) -> MeasuredFasta:
        self.paths.append(path)
        length = 2 if path.name.startswith("NG_000001") else 4
        return MeasuredFasta(
            header="insulin",
            header_words=("insulin",),
            gene_length=length,
            sequence="A" * length,
        )


class _FakeCriteriaSink:
    def __init__(self) -> None:
        self.rows: tuple[CriteriaRow, ...] = ()
        self.path = Path("/criteria/accession_criteria.csv")

    def write(self, rows: tuple[CriteriaRow, ...] | list[CriteriaRow]) -> Path:
        self.rows = tuple(rows)
        return self.path


class _FakeRepresentativeSink:
    def __init__(self) -> None:
        self.rows: tuple[CriteriaRow, ...] = ()

    def write(self, rows: tuple[CriteriaRow, ...] | list[CriteriaRow]) -> Path:
        self.rows = tuple(rows)
        return Path("/representative/NCBI_representative_seq.csv")


class _FakeReader:
    def read(self) -> tuple[ChosenAccession, ...]:
        return (ChosenAccession(query="insulin", accession="FROM-READER"),)


class _FakeOpener:
    def __init__(self) -> None:
        self.path: Path | None = None

    def open(self, path: Path) -> _FakeReader:
        self.path = path
        return _FakeReader()


class _FakeGenes:
    def __init__(self) -> None:
        self.chosen: tuple[ChosenAccession, ...] = ()

    def write(self, chosen: tuple[ChosenAccession, ...]) -> Path:
        self.chosen = chosen
        return Path("/genes/genes.csv")
