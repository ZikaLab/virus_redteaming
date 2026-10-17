"""Annotation preserves every catalogue field except Schedule 5."""

from __future__ import annotations

from virus_redteaming.catalogue.schedule5_annotate import AnnotationResult, CatalogueRow
from virus_redteaming.catalogue.schedule5_match import VirusNameInteractor


def test_virus_column_unchanged(
    catalogue_rows: tuple[CatalogueRow, ...],
    annotation_result: AnnotationResult,
) -> None:
    assert [row.virus for row in catalogue_rows] == [row.virus for row in annotation_result.rows]


def test_only_schedule_5_field_changes(
    catalogue_rows: tuple[CatalogueRow, ...],
    annotation_result: AnnotationResult,
) -> None:
    assert len(catalogue_rows) == len(annotation_result.rows) == 232
    for original, updated in zip(catalogue_rows, annotation_result.rows):
        assert original.family == updated.family
        assert original.genus == updated.genus
        assert original.virus == updated.virus
        assert original.hazard_group == updated.hazard_group
        assert updated.schedule_5 in {"0", "1"}


def test_each_matched_schedule5_name_has_a_flagged_virus_row(
    interactor: VirusNameInteractor,
    annotation_result: AnnotationResult,
) -> None:
    flagged = [row for row in annotation_result.rows if row.schedule_5 == "1"]
    for name in annotation_result.matched_names:
        assert any(interactor.interacts(row.virus, (name,)) for row in flagged)
    for name in annotation_result.unmatched_names:
        assert all(not interactor.interacts(row.virus, (name,)) for row in flagged)


def test_schedule5_column_is_binary_and_covers_all_rows(
    annotation_result: AnnotationResult,
) -> None:
    ones = sum(1 for row in annotation_result.rows if row.schedule_5 == "1")
    zeros = sum(1 for row in annotation_result.rows if row.schedule_5 == "0")
    assert ones + zeros == 232
    assert all(row.schedule_5 in {"0", "1"} for row in annotation_result.rows)
