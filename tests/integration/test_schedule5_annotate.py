"""Annotate a temporary copy of the catalogue. Do not write output/viruses.csv."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from virus_redteaming.catalogue.schedule5_annotate import (
    AnnotateSchedule5,
    CatalogueCsvReader,
    Schedule5CsvAnnotator,
    Schedule5CsvWriter,
    UnmatchedNameSink,
)
from virus_redteaming.catalogue.schedule5_match import VirusNameInteractor, VirusNameNormaliser
from virus_redteaming.catalogue.schedule5_source import MarkdownBulletNameSource

from tests.conftest import (
    ICTV_CSV,
    SCHEDULE5_MD,
    UNMATCHED_NAME,
    VIRUSES_CSV,
    count_csv_data_rows,
)


def _workflow() -> AnnotateSchedule5:
    return AnnotateSchedule5(
        source=MarkdownBulletNameSource(),
        reader=CatalogueCsvReader(),
        annotator=Schedule5CsvAnnotator(VirusNameInteractor(VirusNameNormaliser())),
        writer=Schedule5CsvWriter(),
        unmatched_sink=UnmatchedNameSink(),
    )


@pytest.fixture
def tmp_catalogue_copy(tmp_path: Path) -> Path:
    destination = tmp_path / "viruses.csv"
    shutil.copy(VIRUSES_CSV, destination)
    return destination


def test_inventory_counts_on_disk() -> None:
    assert count_csv_data_rows(VIRUSES_CSV) == 232
    assert len(MarkdownBulletNameSource().load(SCHEDULE5_MD)) == 46
    assert count_csv_data_rows(ICTV_CSV) == 7230


def test_annotate_preserves_row_count_and_virus_names(tmp_catalogue_copy: Path) -> None:
    repo_before = VIRUSES_CSV.read_bytes()
    reader = CatalogueCsvReader()
    snapshot = reader.read(tmp_catalogue_copy)
    unmatched_path = tmp_catalogue_copy.parent / UNMATCHED_NAME
    _workflow().run(SCHEDULE5_MD, tmp_catalogue_copy, unmatched_path)
    updated = reader.read(tmp_catalogue_copy)
    assert len(snapshot) == len(updated) == 232
    assert [row.virus for row in snapshot] == [row.virus for row in updated]
    for original, annotated in zip(snapshot, updated):
        assert (original.family, original.genus, original.virus, original.hazard_group) == (
            annotated.family,
            annotated.genus,
            annotated.virus,
            annotated.hazard_group,
        )
        assert annotated.schedule_5 in {"0", "1"}
    assert VIRUSES_CSV.read_bytes() == repo_before


def test_schedule5_list_is_fully_accounted_for(
    tmp_catalogue_copy: Path,
    schedule5_names: tuple[str, ...],
) -> None:
    unmatched_path = tmp_catalogue_copy.parent / UNMATCHED_NAME
    result = _workflow().run(SCHEDULE5_MD, tmp_catalogue_copy, unmatched_path)
    unmatched_lines = unmatched_path.read_text(encoding="utf-8").splitlines()
    assert len(result.matched_names) + len(unmatched_lines) == 46
    assert set(schedule5_names) == set(result.matched_names) | set(unmatched_lines)
