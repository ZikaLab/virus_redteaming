"""GenBank cells become NCBI accession codes."""

from virus_redteaming.nen_accession.parse import GenBankAccessionParser


def _join(field: str) -> str:
    return GenBankAccessionParser().join(field)


def test_single_accession() -> None:
    assert _join("U87411") == "U87411"


def test_semicolon_separated_accessions_keep_order() -> None:
    assert _join("KX949586; KX949587; KX949588") == "KX949586; KX949587; KX949588"


def test_segment_labels_are_dropped() -> None:
    assert _join("L: ON648820; S: ON648824") == "ON648820; ON648824"


def test_dna_component_labels_are_dropped() -> None:
    field = "DNA-C: EF546812; DNA-M: EF546811; DNA-S: EF546810"
    assert _join(field) == "EF546812; EF546811; EF546810"


def test_coordinate_range_is_dropped() -> None:
    field = "Seg1: AH009795(1.3949); Seg2: AH009795(4050.7926); Seg4: AF403390"
    assert _join(field) == "AH009795; AF403390"


def test_space_before_coordinate_range() -> None:
    assert _join("LK928904 (2253.10260)") == "LK928904"


def test_version_suffix_stays_on_the_code() -> None:
    assert _join("NC_001474.1") == "NC_001474.1"


def test_eight_digit_accession_is_not_cut_to_six() -> None:
    assert _join("BK013673") == "BK013673"


def test_refseq_style_code() -> None:
    assert _join("NC_001474") == "NC_001474"


def test_repeated_code_is_kept_once() -> None:
    assert _join("AF052015; AF052015") == "AF052015"


def test_empty_cell() -> None:
    assert _join("") == ""
    assert _join("   ") == ""


def test_no_genbank_entry_yields_no_code() -> None:
    assert _join("No entry in Genbank") == ""


def test_non_breaking_space_does_not_hide_a_code() -> None:
    assert _join("U87411\xa0") == "U87411"


def test_one_letter_and_two_letter_codes_in_one_cell() -> None:
    assert _join("M14627; AF304460") == "M14627; AF304460"


def test_trailing_semicolon_does_not_add_an_empty_code() -> None:
    assert _join("AF052015;") == "AF052015"
