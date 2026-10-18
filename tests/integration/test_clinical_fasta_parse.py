"""Parse through the real object graph. These tests do not call NCBI."""

import csv
from pathlib import Path

import pytest

from virus_redteaming.clinical_fasta.__main__ import main

_GENES_HEADER = [
    "Family",
    "Genus",
    "Virus",
    "Human pathogen hazard group",
    "Schedule 5",
]
_MITO = "human[organism] mitochondrion genome"
_WORKED = "OZ567094.1 Homo sapiens genome assembly, organelle: mitochondrion"


def test_parse_command_writes_the_three_tables(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _refuse_ncbi(monkeypatch)
    output = _clinical_tree(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["parse"]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert [Path(line).name for line in printed] == [
        "accession_criteria.csv",
        "NCBI_representative_seq.csv",
        "genes.csv",
    ]
    criteria = _criteria(output / "accession_criteria.csv")
    assert [row["Accession"] for row in criteria] == [
        "NG_000001.1",
        "NG_000002.1",
        "NG_000003.1",
        "NG_000004.1",
        "NG_000005.1",
        "NG_000011.1",
        "NG_000012.1",
        "NG_000021.1",
    ]
    assert list(criteria[0])[-1] == "Representative"
    assert criteria[0]["Failure"] == ""
    assert criteria[0]["Representative"] == "0"
    assert criteria[0]["WordMatchCount"] == "2"
    assert criteria[0]["Header"] == _WORKED
    assert criteria[1]["Failure"] == ""
    assert criteria[1]["Representative"] == "0"
    assert criteria[1]["WordMatchCount"] == "1"
    assert criteria[2]["Accession"] == "NG_000003.1"
    assert criteria[2]["Representative"] == "1"
    assert criteria[2]["InOrderMatch"] == "0"
    assert criteria[2]["WordMatchCount"] == "2"
    assert criteria[2]["GeneLength"] == "12"
    assert criteria[2]["Failure"] == ""
    assert criteria[3]["Failure"] == "missing fasta"
    assert criteria[3]["GeneLength"] == ""
    assert criteria[3]["Header"] == ""
    assert criteria[4]["Failure"] == "longer than 40000 bp"
    assert criteria[4]["WithinUpperCutoff"] == "0"
    assert criteria[4]["Header"] == "genome of the mitochondrion"
    assert criteria[4]["WordMatchCount"] == "2"
    assert criteria[5]["InOrderMatch"] == "1"
    assert criteria[5]["AdjacentMatch"] == "1"
    assert criteria[5]["Failure"] == ""
    assert criteria[5]["Representative"] == "0"
    assert criteria[6]["Representative"] == "1"
    assert criteria[6]["InOrderMatch"] == "1"
    assert criteria[6]["AdjacentMatch"] == "1"
    assert criteria[7]["Failure"] == "no screened words"
    assert criteria[7]["GeneLength"] == "4"
    assert criteria[7]["Header"] == "kept header"
    assert criteria[7]["InOrderMatch"] == "0"
    assert criteria[7]["AdjacentMatch"] == "0"
    assert criteria[7]["WordMatchCount"] == "0"
    raw = (output / "accession_criteria.csv").read_text(encoding="utf-8")
    assert "assembly\\, organelle" in raw
    assert '"assembly, organelle"' not in raw
    representative = _plain(output / "NCBI_representative_seq.csv")
    assert representative[1:] == [
        [_MITO, "NG_000003.1", "12", "A" * 12, "1"],
        ["human insulin", "NG_000012.1", "4", "ACGT", "1"],
    ]
    genes = _plain(output / "genes.csv")
    assert genes[0] == [*_GENES_HEADER, "Accession"]
    assert genes[0].count("Accession") == 1
    assert [row[-1] for row in genes[1:]] == [
        "NG_000003.1",
        "NG_000012.1",
        "",
        "",
        "NG_000003.1",
    ]
    assert genes[1][:2] == ["alpha", "beta"]
    assert genes[5][:2] == ["alpha", "beta"]


def test_parse_command_second_run_keeps_one_accession_column(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _refuse_ncbi(monkeypatch)
    output = _clinical_tree(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["parse"]) == 0
    capsys.readouterr()
    assert main(["parse"]) == 0
    genes = _plain(output / "genes.csv")
    assert genes[0].count("Accession") == 1
    assert genes[0][-1] == "Accession"
    assert [row[-1] for row in genes[1:]] == [
        "NG_000003.1",
        "NG_000012.1",
        "",
        "",
        "NG_000003.1",
    ]


def test_parse_command_bad_fasta_leaves_genes_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _refuse_ncbi(monkeypatch)
    output = tmp_path / "output"
    genes_dir = output / "clinical_genes"
    genes_dir.mkdir(parents=True)
    genes = output / "genes.csv"
    genes.write_text("Virus,Note\ninsulin,keep-me\n", encoding="utf-8")
    _write_csv(
        output / "accessions.csv",
        ["Virus", "Rank", "Accession"],
        [["insulin", "1", "NG_000001.1"]],
    )
    (genes_dir / "NG_000001.1.fasta").write_text("", encoding="utf-8")
    criteria = output / "accession_criteria.csv"
    criteria.write_text("previous\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert main(["parse"]) == 1
    assert "no header" in capsys.readouterr().err
    assert genes.read_text(encoding="utf-8") == "Virus,Note\ninsulin,keep-me\n"
    assert criteria.read_text(encoding="utf-8") == "previous\n"
    assert list(output.glob("*.tmp")) == []


def _refuse_ncbi(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("parse called NCBI")

    monkeypatch.setattr(
        "virus_redteaming.clinical_fasta.__main__.BiopythonEntrezClient",
        refuse,
    )


def _clinical_tree(tmp_path: Path) -> Path:
    output = tmp_path / "output"
    genes_dir = output / "clinical_genes"
    genes_dir.mkdir(parents=True)
    _write_csv(
        output / "genes.csv",
        _GENES_HEADER,
        [
            ["alpha", "beta", _MITO, "group", "five"],
            ["", "", " human insulin ", "", ""],
            ["", "", "[organism]", "", ""],
            ["", "", "Human insulin", "", ""],
            ["alpha", "beta", _MITO, "group", "five"],
        ],
    )
    _write_csv(
        output / "accessions.csv",
        ["Virus", "Rank", "Accession"],
        [
            [_MITO, "1", "NG_000001.1"],
            [_MITO, "2", "NG_000002.1"],
            [_MITO, "3", "NG_000003.1"],
            [_MITO, "4", "NG_000004.1"],
            [_MITO, "5", "NG_000005.1"],
            ["human insulin", "1", "NG_000011.1"],
            ["human insulin", "2", "NG_000012.1"],
            ["[organism]", "1", "NG_000021.1"],
        ],
    )
    _fasta(genes_dir, "NG_000001.1", _WORKED, "ACGTACGT")
    _fasta(genes_dir, "NG_000002.1", "Homo sapiens mitochondrion", "A" * 30)
    _fasta(genes_dir, "NG_000003.1", "genome mitochondrion", "A" * 12)
    _fasta(genes_dir, "NG_000005.1", "genome of the mitochondrion", "A" * 40_001)
    _fasta(genes_dir, "NG_000011.1", "human insulin", "AC")
    _fasta(genes_dir, "NG_000012.1", "human insulin", "ACGT")
    _fasta(genes_dir, "NG_000021.1", "kept header", "AAAA")
    return output


def _fasta(directory: Path, accession: str, header: str, sequence: str) -> None:
    (directory / f"{accession}.fasta").write_text(
        f">{header}\n{sequence}\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


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
