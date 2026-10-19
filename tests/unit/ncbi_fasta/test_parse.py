"""Segment grammar for a GenBank cell."""

import pytest

from virus_redteaming.ncbi_fasta.errors import NcbiFastaInputError
from virus_redteaming.ncbi_fasta.parse import GenBankSegmentParser


def test_labelled_segments_keep_the_code_after_each_colon() -> None:
    codes = GenBankSegmentParser().codes("RNA1: V00603; RNA2: J02151")
    assert codes == ("V00603", "J02151")


def test_bare_accession_is_kept() -> None:
    assert GenBankSegmentParser().codes("U87411") == ("U87411",)
    assert GenBankSegmentParser().codes("AF052015;") == ("AF052015",)


def test_coordinate_suffix_is_stripped_after_colon() -> None:
    cell = "Seg1: AH009795(1.3949); Seg4: AF403390"
    assert GenBankSegmentParser().codes(cell) == ("AH009795", "AF403390")


def test_wgs_accession_is_rejected() -> None:
    with pytest.raises(NcbiFastaInputError):
        GenBankSegmentParser().codes("CASDWV010000980")


def test_repeated_code_inside_one_cell_is_kept_once() -> None:
    assert GenBankSegmentParser().codes("AF052015; AF052015") == ("AF052015",)


def test_blank_and_nbsp_cells_are_empty_or_stripped() -> None:
    parser = GenBankSegmentParser()
    assert parser.codes("   ") == ()
    assert parser.codes("\xa0") == ()
    assert parser.codes("\xa0U87411\xa0") == ("U87411",)


def test_malformed_populated_cell_raises_input_error() -> None:
    parser = GenBankSegmentParser()
    cells = (
        ";",
        "No entry in Genbank",
        "RNA1: ???",
        ": V00603",
        "L: V00603; ; S: J02151",
    )
    for cell in cells:
        with pytest.raises(NcbiFastaInputError):
            parser.codes(cell)


def test_other_segment_labels_keep_the_code() -> None:
    parser = GenBankSegmentParser()
    assert parser.codes("L: AY358022; S: AY358023") == ("AY358022", "AY358023")
    assert parser.codes("Seg1: AF133428; Seg2: AF139758") == ("AF133428", "AF139758")
    dna = "DNA-C: EF546812; DNA-M: EF546811"
    assert parser.codes(dna) == ("EF546812", "EF546811")
