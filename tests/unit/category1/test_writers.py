"""CSV headers, catalogue indexes, and Category 1 constants."""

from __future__ import annotations

import csv
from pathlib import Path

from virus_redteaming.category1.models import IctvSpecies, NenRow
from virus_redteaming.category1.write import (
    CAT1_HEADER,
    NEN_HEADER,
    IctvCat1Writer,
    NenReader,
    NenWriter,
)


def _nen(viruses: str, nen_virus: str = "e") -> NenRow:
    return NenRow(0, "Fam", "Genus", "NenGenus", viruses, nen_virus, "")


def test_nen_header(tmp_path: Path) -> None:
    path = tmp_path / "nen.csv"
    NenWriter().write(path, (_nen("Dengue virus"),))
    with path.open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle))
    assert header == list(NEN_HEADER)


def test_nen_reader_shares_one_index_across_serotypes(tmp_path: Path) -> None:
    path = tmp_path / "nen.csv"
    NenWriter().write(
        path,
        (
            _nen("Dengue virus", "type 1"),
            _nen("Dengue virus", "type 2"),
            _nen("Dengue virus", "type 3"),
        ),
    )
    rows = NenReader().read(path)
    assert {row.catalogue_index for row in rows} == {0}


def test_nen_reader_restarts_index_after_a_different_row(tmp_path: Path) -> None:
    path = tmp_path / "nen.csv"
    NenWriter().write(
        path,
        (
            _nen("Same", "a"),
            _nen("Same", "b"),
            _nen("Other", "c"),
            _nen("Same", "d"),
        ),
    )
    rows = NenReader().read(path)
    assert [row.catalogue_index for row in rows] == [0, 0, 1, 2]


def test_cat1_header_and_constants(tmp_path: Path) -> None:
    path = tmp_path / "cat1.csv"
    blank = IctvSpecies(
        0, "Blank species", "blank virus", "Fam", "Genus", "King", "", ""
    )
    segmented = IctvSpecies(
        1,
        "Seg species",
        "seg virus",
        "Fam",
        "Genus",
        "King",
        "L: aaa; M: bbb; S: ccc",
        "L: NC_1; M: NC_2; S: NC_3",
    )
    IctvCat1Writer().write(path, (blank, segmented))
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0].keys()) == list(CAT1_HEADER)
    assert rows[0]["Human pathogen hazard group"] == "1"
    assert rows[0]["Schedule 5"] == "0"
    assert rows[0]["Issues"] == ""
    assert rows[0]["GenBank accessions"] == ""
    assert rows[1]["GenBank accessions"] == "L: aaa; M: bbb; S: ccc"
    assert rows[1]["RefSeq accessions"] == "L: NC_1; M: NC_2; S: NC_3"
