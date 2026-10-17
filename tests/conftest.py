"""Shared pytest fixtures. Keep fakes here when they implement core Protocols."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from virus_redteaming.catalogue.schedule5_annotate import (
    AnnotationResult,
    CatalogueCsvReader,
    CatalogueRow,
    Schedule5CsvAnnotator,
)
from virus_redteaming.catalogue.schedule5_match import VirusNameInteractor, VirusNameNormaliser
from virus_redteaming.catalogue.schedule5_source import MarkdownBulletNameSource

# tests/conftest.py sits one directory under the repo. parents[3] is for a file
# under tests/unit/catalogue/ or tests/integration/, not for this file.
REPO_ROOT = Path(__file__).resolve().parents[1]
VIRUSES_CSV = REPO_ROOT / "output" / "viruses.csv"
SCHEDULE5_MD = REPO_ROOT / "docs" / "schedule5.md"
ICTV_CSV = REPO_ROOT / "docs" / "ICTV_RNA_virus_species_MSL41.csv"
UNMATCHED_NAME = "schedule5_unmatched.txt"
ICTV_RNA_ROW_COUNT = 7230
VIRUSES_CSV_ROW_COUNT = 232
SCHEDULE5_NAME_COUNT = 46


def count_csv_data_rows(path: Path) -> int:
    with path.open(encoding="utf-8", newline="") as handle:
        return len(list(csv.reader(handle))) - 1


@pytest.fixture
def schedule5_names() -> tuple[str, ...]:
    return MarkdownBulletNameSource().load(SCHEDULE5_MD)


@pytest.fixture
def catalogue_rows() -> tuple[CatalogueRow, ...]:
    return CatalogueCsvReader().read(VIRUSES_CSV)


@pytest.fixture
def interactor() -> VirusNameInteractor:
    return VirusNameInteractor(VirusNameNormaliser())


@pytest.fixture
def annotator(interactor: VirusNameInteractor) -> Schedule5CsvAnnotator:
    return Schedule5CsvAnnotator(interactor)


@pytest.fixture
def annotation_result(
    annotator: Schedule5CsvAnnotator,
    catalogue_rows: tuple[CatalogueRow, ...],
    schedule5_names: tuple[str, ...],
) -> AnnotationResult:
    return annotator.annotate(catalogue_rows, schedule5_names)
