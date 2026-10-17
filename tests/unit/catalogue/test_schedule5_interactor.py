"""Schedule-5 name partition and the spot checks from spec.schedule5.md."""

from __future__ import annotations

from virus_redteaming.catalogue.schedule5_annotate import AnnotationResult


def test_schedule5_names_partition_into_matched_and_unmatched(
    schedule5_names: tuple[str, ...],
    annotation_result: AnnotationResult,
) -> None:
    matched = annotation_result.matched_names
    unmatched = set(annotation_result.unmatched_names)
    assert len(matched) + len(unmatched) == 46
    assert set(schedule5_names) == matched | unmatched
    assert matched.isdisjoint(unmatched)


def _schedule_5_for(annotation_result: AnnotationResult, fragment: str) -> str:
    matches = [row for row in annotation_result.rows if fragment in row.virus]
    assert len(matches) == 1
    return matches[0].schedule_5


def test_sars_cov_2_is_not_schedule_5(annotation_result: AnnotationResult) -> None:
    assert _schedule_5_for(annotation_result, "SARS-CoV-2") == "0"


def test_sars_cov_1_is_schedule_5(annotation_result: AnnotationResult) -> None:
    assert _schedule_5_for(annotation_result, "SARS-CoV-1") == "1"


def test_spot_checks(annotation_result: AnnotationResult) -> None:
    by_virus = {row.virus: row.schedule_5 for row in annotation_result.rows}
    assert by_virus["Andes virus"] == "0"
    assert by_virus["Dengue virus"] == "1"
    assert by_virus["Louping ill virus"] == "1"
    assert by_virus["Yellow fever virus"] == "1"
    assert by_virus["Zika virus"] == "0"
    assert by_virus["Guanarito virus"] == "1"
    assert by_virus["Zaire ebolavirus"] == "1"
    assert by_virus["Adenoviridae spp. known to be pathogenic in humans"] == "0"
