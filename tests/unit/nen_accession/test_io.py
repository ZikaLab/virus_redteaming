"""CSV readers and the nen writer."""

import csv
from pathlib import Path

import pytest

from virus_redteaming.nen_accession.errors import NenTableError, VmrTableError
from virus_redteaming.nen_accession.io import (
    NEN_FIELDS,
    NenAccessionWriter,
    NenCsvReader,
    VmrCsvReader,
)
from virus_redteaming.nen_accession.models import NenVirusRecord


def _nen_record() -> NenVirusRecord:
    return NenVirusRecord(
        family="Flaviviridae",
        genus="Orthoflavivirus",
        nen_genus="Orthoflavivirus",
        viruses="Ilhéus virus",
        nen_virus="Ilhéus virus",
        hazard_group="3",
        schedule_5="0",
        issues="",
        ncbi_accession="AY632539",
    )


def test_vmr_reader_keeps_exemplar_flag_and_raw_accession(tmp_path: Path) -> None:
    path = tmp_path / "vmr.csv"
    path.write_text(
        "Virus name(s),Exemplar or additional isolate,Virus GENBANK accession\n"
        "dengue virus type 2,E,U87411\n"
        "dengue virus type 1,A,U88536\n",
        encoding="utf-8",
    )
    isolates = VmrCsvReader().read(path)
    assert isolates[0].is_exemplar is True
    assert isolates[0].genbank_field == "U87411"
    assert isolates[1].is_exemplar is False
    assert isolates[1].virus_name == "dengue virus type 1"


def test_vmr_reader_rejects_a_missing_accession_column(tmp_path: Path) -> None:
    path = tmp_path / "vmr.csv"
    path.write_text(
        "Virus name(s),Exemplar or additional isolate\nX,E\n",
        encoding="utf-8",
    )
    with pytest.raises(VmrTableError):
        VmrCsvReader().read(path)


def test_nen_reader_rejects_a_missing_nen_virus_column(tmp_path: Path) -> None:
    path = tmp_path / "nen.csv"
    path.write_text("Family,Genus\nA,B\n", encoding="utf-8")
    with pytest.raises(NenTableError):
        NenCsvReader().read(path)


def test_writer_inserts_ncbi_accession_after_nen_virus(tmp_path: Path) -> None:
    path = tmp_path / "nen.csv"
    NenAccessionWriter().write(path, (_nen_record(),))
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == list(NEN_FIELDS)
    assert rows[1][4] == "Ilhéus virus"
    assert rows[1][5] == "AY632539"
    assert rows[1][6] == "3"
    assert rows[1][8] == ""


def test_reader_ignores_an_existing_ncbi_column(tmp_path: Path) -> None:
    path = tmp_path / "nen.csv"
    NenAccessionWriter().write(path, (_nen_record(),))
    rows = NenCsvReader().read(path)
    assert rows[0].ncbi_accession == ""
    assert rows[0].nen_virus == "Ilhéus virus"
    assert rows[0].hazard_group == "3"


def test_round_trip_preserves_diacritics_and_hazard(tmp_path: Path) -> None:
    path = tmp_path / "nen.csv"
    NenAccessionWriter().write(path, (_nen_record(),))
    text = path.read_text(encoding="utf-8")
    assert "Ilhéus virus" in text
    assert "\n" in text
    assert "\r" not in text
