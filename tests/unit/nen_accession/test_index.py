"""Which VMR row stands for a virus name."""

from virus_redteaming.nen_accession.index import ExemplarVirusIndex
from virus_redteaming.nen_accession.models import VmrIsolate


def _isolate(name: str, exemplar: bool, accession: str) -> VmrIsolate:
    return VmrIsolate(name, exemplar, accession)


def test_exact_name_returns_that_row() -> None:
    index = ExemplarVirusIndex((_isolate("dengue virus type 2", True, "U87411"),))
    found = index.isolate("dengue virus type 2")
    assert found is not None
    assert found.genbank_field == "U87411"


def test_non_breaking_space_and_padding_still_match() -> None:
    index = ExemplarVirusIndex(
        (_isolate("dengue virus type 2\xa0", True, "U87411"),)
    )
    found = index.isolate("  dengue virus type 2")
    assert found is not None
    assert found.genbank_field == "U87411"


def test_case_difference_does_not_match() -> None:
    index = ExemplarVirusIndex((_isolate("Dengue virus type 2", True, "U87411"),))
    assert index.isolate("dengue virus type 2") is None


def test_semicolon_synonym_is_not_a_separate_key() -> None:
    index = ExemplarVirusIndex(
        (
            _isolate(
                "canine minute virus; minute virus of canines",
                True,
                "FJ214110",
            ),
        )
    )
    assert index.isolate("canine minute virus") is None
    found = index.isolate("canine minute virus; minute virus of canines")
    assert found is not None


def test_exemplar_wins_when_an_additional_isolate_is_listed_first() -> None:
    index = ExemplarVirusIndex(
        (
            _isolate("Zika virus", False, "KY766069"),
            _isolate("Zika virus", True, "AY632535"),
            _isolate("Zika virus", False, "KJ776791"),
        )
    )
    found = index.isolate("Zika virus")
    assert found is not None
    assert found.genbank_field == "AY632535"


def test_first_exemplar_wins_when_two_are_marked() -> None:
    index = ExemplarVirusIndex(
        (
            _isolate("Zika virus", True, "AY632535"),
            _isolate("Zika virus", True, "OTHER"),
        )
    )
    found = index.isolate("Zika virus")
    assert found is not None
    assert found.genbank_field == "AY632535"


def test_first_row_wins_when_no_exemplar_exists() -> None:
    index = ExemplarVirusIndex(
        (
            _isolate("poliovirus 2", False, "M12197"),
            _isolate("poliovirus 2", False, "X00595"),
        )
    )
    found = index.isolate("poliovirus 2")
    assert found is not None
    assert found.genbank_field == "M12197"


def test_blank_virus_name_is_not_indexed() -> None:
    index = ExemplarVirusIndex((_isolate("  ", True, "U87411"),))
    assert index.isolate("") is None
    assert index.isolate("   ") is None


def test_different_names_do_not_share_an_accession() -> None:
    index = ExemplarVirusIndex(
        (
            _isolate("dengue virus type 1", False, "U88536"),
            _isolate("dengue virus type 2", True, "U87411"),
        )
    )
    first = index.isolate("dengue virus type 1")
    second = index.isolate("dengue virus type 2")
    assert first is not None and second is not None
    assert first.genbank_field == "U88536"
    assert second.genbank_field == "U87411"
