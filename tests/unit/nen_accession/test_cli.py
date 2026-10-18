"""The assign-nen-accessions command writes the column and prints misses."""

import csv
from pathlib import Path

import pytest

from virus_redteaming.__main__ import main

_NEN_HEADER = (
    "Family,Genus,NEN genus,Viruses,NEN virus,"
    "Human pathogen hazard group,Schedule 5,Issues\n"
)


def test_cli_copies_accession_and_prints_the_miss(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nen = tmp_path / "nen.csv"
    vmr = tmp_path / "vmr.csv"
    nen.write_text(
        _NEN_HEADER
        + "F,Orthoflavivirus,Orthoflavivirus,Dengue virus,dengue virus type 2,3,1,\n"
        + "P,Bocaparvovirus,Bocaparvovirus,Human bocavirus,human bocavirus 3,2,0,\n"
        + "Adenoviridae,,,Adenoviridae spp.,,2,0,genus not in ICTV\n",
        encoding="utf-8",
    )
    vmr.write_text(
        "Virus name(s),Exemplar or additional isolate,Virus GENBANK accession\n"
        "dengue virus type 2,E,U87411\n",
        encoding="utf-8",
    )
    status = main(["assign-nen-accessions", "--nen", str(nen), "--vmr", str(vmr)])
    assert status == 0
    with nen.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["NCBI accession"] == "U87411"
    assert rows[0]["Human pathogen hazard group"] == "3"
    assert rows[0]["Schedule 5"] == "1"
    assert rows[1]["NCBI accession"] == ""
    assert rows[1]["Issues"] == ""
    assert rows[2]["NCBI accession"] == ""
    assert rows[2]["Issues"] == "genus not in ICTV"
    printed = capsys.readouterr().out
    assert "matched 1 rows" in printed
    assert "unmatched NEN virus: human bocavirus 3" in printed
    assert "blank NEN virus: 1" in printed


def test_cli_is_idempotent(tmp_path: Path) -> None:
    nen = tmp_path / "nen.csv"
    vmr = tmp_path / "vmr.csv"
    nen.write_text(
        _NEN_HEADER + "F,G,G,V,dengue virus type 2,3,1,\n",
        encoding="utf-8",
    )
    vmr.write_text(
        "Virus name(s),Exemplar or additional isolate,Virus GENBANK accession\n"
        "dengue virus type 2,E,U87411\n",
        encoding="utf-8",
    )
    assert main(["assign-nen-accessions", "--nen", str(nen), "--vmr", str(vmr)]) == 0
    first = nen.read_bytes()
    assert main(["assign-nen-accessions", "--nen", str(nen), "--vmr", str(vmr)]) == 0
    assert nen.read_bytes() == first
