"""Inventory locks for the schedule-5 list, the catalogue, and the ICTV table."""

from __future__ import annotations

from virus_redteaming.catalogue.schedule5_annotate import CatalogueRow

from tests.conftest import ICTV_CSV, count_csv_data_rows


def test_schedule5_md_has_46_bullets(schedule5_names: tuple[str, ...]) -> None:
    assert len(schedule5_names) == 46
    assert len(set(schedule5_names)) == 46


def test_viruses_csv_has_232_data_rows(catalogue_rows: tuple[CatalogueRow, ...]) -> None:
    assert len(catalogue_rows) == 232


def test_ictv_msl41_has_7230_data_rows() -> None:
    assert count_csv_data_rows(ICTV_CSV) == 7230
