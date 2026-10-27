"""NEN rows receive the accession of the matched VMR isolate."""

from virus_redteaming.nen_accession.assign import NenAccessionAssigner
from virus_redteaming.nen_accession.index import ExemplarVirusIndex
from virus_redteaming.nen_accession.models import NenVirusRecord, VmrIsolate
from virus_redteaming.nen_accession.parse import GenBankAccessionParser


def _row(
    nen_virus: str,
    viruses: str = "Dengue virus",
    issues: str = "",
) -> NenVirusRecord:
    return NenVirusRecord(
        family="Flaviviridae",
        genus="Orthoflavivirus",
        nen_genus="Orthoflavivirus",
        viruses=viruses,
        nen_virus=nen_virus,
        hazard_group="3",
        schedule_5="1",
        issues=issues,
    )


def _assign(rows: tuple[NenVirusRecord, ...], isolates: tuple[VmrIsolate, ...]):
    return NenAccessionAssigner(
        ExemplarVirusIndex(isolates),
        GenBankAccessionParser(),
    ).assign(rows)


def test_matching_row_receives_segment_codes() -> None:
    rows, report = _assign(
        (_row("Dàbiéshān virus"),),
        (VmrIsolate("Dàbiéshān virus", True, "L: ON648820; S: ON648824"),),
    )
    assert rows[0].ncbi_accession == "ON648820; ON648824"
    assert report.matched == 1
    assert report.unmatched_names == ()


def test_other_columns_stay_unchanged() -> None:
    original = _row("dengue virus type 2", issues="kept")
    rows, _report = _assign(
        (original,),
        (VmrIsolate("dengue virus type 2", True, "U87411"),),
    )
    updated = rows[0]
    assert updated.family == original.family
    assert updated.genus == original.genus
    assert updated.nen_genus == original.nen_genus
    assert updated.viruses == original.viruses
    assert updated.nen_virus == original.nen_virus
    assert updated.hazard_group == "3"
    assert updated.schedule_5 == "1"
    assert updated.issues == "kept"
    assert updated.ncbi_accession == "U87411"


def test_serotype_rows_of_one_catalogue_virus_get_different_codes() -> None:
    rows, report = _assign(
        (
            _row("dengue virus type 2"),
            _row("dengue virus type 1"),
            _row("dengue virus type 4"),
        ),
        (
            VmrIsolate("dengue virus type 2", True, "U87411"),
            VmrIsolate("dengue virus type 1", False, "U88536"),
            VmrIsolate("dengue virus type 3", False, "M93130"),
            VmrIsolate("dengue virus type 4", False, "AF326573"),
        ),
    )
    assert [row.ncbi_accession for row in rows] == ["U87411", "U88536", "AF326573"]
    assert report.matched == 3


def test_blank_nen_virus_is_not_an_unmatched_name() -> None:
    rows, report = _assign(
        (_row(""),),
        (VmrIsolate("", True, "U87411"),),
    )
    assert rows[0].ncbi_accession == ""
    assert report.blank_nen_virus == 1
    assert report.matched == 0
    assert report.unmatched_names == ()


def test_missing_name_is_reported_once_and_left_blank() -> None:
    rows, report = _assign(
        (_row("human bocavirus 3"), _row("human bocavirus 3")),
        (VmrIsolate("human bocavirus 1", True, "JQ923422"),),
    )
    assert rows[0].ncbi_accession == ""
    assert rows[1].ncbi_accession == ""
    assert report.unmatched_names == ("human bocavirus 3",)
    assert report.matched == 0


def test_additional_isolate_is_used_only_when_no_exemplar_exists() -> None:
    rows, _report = _assign(
        (_row("poliovirus 2", viruses="Poliovirus 2"),),
        (
            VmrIsolate("poliovirus 2", False, "M12197"),
            VmrIsolate("poliovirus 2", False, "X00595"),
        ),
    )
    assert rows[0].ncbi_accession == "M12197"


def test_exemplar_is_preferred_over_an_earlier_additional_isolate() -> None:
    rows, _report = _assign(
        (_row("Zika virus", viruses="Zika virus"),),
        (
            VmrIsolate("Zika virus", False, "KY766069"),
            VmrIsolate("Zika virus", True, "AY632535"),
        ),
    )
    assert rows[0].ncbi_accession == "AY632535"
