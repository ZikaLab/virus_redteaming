"""The merged table yields distinct codes and a blank-row count."""

from pathlib import Path

import pytest

from virus_redteaming.ncbi_fasta.errors import NcbiFastaInputError
from virus_redteaming.ncbi_fasta.parse import GenBankSegmentParser
from virus_redteaming.ncbi_fasta.source import MergedGenBankSource


def _source(path: Path) -> MergedGenBankSource:
    return MergedGenBankSource(path, GenBankSegmentParser())


def test_blank_genbank_cell_is_skipped(tmp_path: Path) -> None:
    table = tmp_path / "merged.csv"
    table.write_text(
        "GenBank accessions\nU87411\n   \nJ02151\n",
        encoding="utf-8",
    )
    scan = _source(table).read()
    assert scan.codes == ("U87411", "J02151")
    assert scan.blank_rows == 1


def test_repeated_accession_across_rows_is_scheduled_once(tmp_path: Path) -> None:
    table = tmp_path / "merged.csv"
    table.write_text(
        "GenBank accessions\nRNA1: V00603\nRNA1: V00603; RNA2: J02151\n",
        encoding="utf-8",
    )
    assert _source(table).read().codes == ("V00603", "J02151")


def test_missing_genbank_header_raises_input_error(tmp_path: Path) -> None:
    table = tmp_path / "merged.csv"
    table.write_text("Virus\nflu\n", encoding="utf-8")
    with pytest.raises(NcbiFastaInputError):
        _source(table).read()


def test_missing_file_raises_input_error(tmp_path: Path) -> None:
    with pytest.raises(NcbiFastaInputError):
        _source(tmp_path / "missing.csv").read()


def test_directory_path_raises_input_error(tmp_path: Path) -> None:
    with pytest.raises(NcbiFastaInputError):
        _source(tmp_path).read()


def test_short_row_and_nbsp_blank_are_skipped(tmp_path: Path) -> None:
    table = tmp_path / "merged.csv"
    table.write_text(
        "Virus,GenBank accessions\nflu\nflu,\xa0\nflu,\xa0V00603\n",
        encoding="utf-8",
    )
    scan = _source(table).read()
    assert scan.blank_rows == 2
    assert scan.codes == ("V00603",)
