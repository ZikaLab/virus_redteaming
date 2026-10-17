"""Optional live parse of misc208.pdf when the file is present."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from virus_redteaming.catalogue.page_window import VIRUS_SECTION_END_PAGE, VIRUS_SECTION_START_PAGE
from virus_redteaming.catalogue.parser import ApprovedVirusListParser
from virus_redteaming.catalogue.paths import CatalogueSourcePath
from virus_redteaming.catalogue.pdf_tables import PdfPlumberTableExtractor

from tests.unit.catalogue.spot_checks import HANTAVIRIDAE_SPOT_CHECKS


def _pdf_path() -> Path:
    override = os.environ.get("APPROVED_LIST_PDF")
    if override:
        return Path(override)
    docs_pdf = CatalogueSourcePath().resolve()
    if docs_pdf.is_file():
        return docs_pdf
    return Path("/Users/michaelgaunt/Downloads/misc208.pdf")


@pytest.fixture(scope="module")
def extracted_rows() -> tuple:
    path = _pdf_path()
    if not path.is_file():
        pytest.skip(f"Approved List PDF not found at {path}")
    return tuple(PdfPlumberTableExtractor().extract(path))


@pytest.fixture(scope="module")
def parsed_records(extracted_rows: tuple) -> tuple:
    return ApprovedVirusListParser().parse(extracted_rows)


def test_extractor_stops_on_printed_page_42(extracted_rows: tuple) -> None:
    pages = {row.printed_page for row in extracted_rows if row.printed_page}
    assert min(pages) >= VIRUS_SECTION_START_PAGE
    assert max(pages) == VIRUS_SECTION_END_PAGE
    assert 43 not in pages
    joined = " ".join(row.agent for row in extracted_rows).casefold()
    assert "annex 1:" not in joined


def test_hantaviridae_order_from_misc208(parsed_records: tuple) -> None:
    hanta = [row for row in parsed_records if row.family == "Hantaviridae"]
    first_five = hanta[:5]
    assert [row.as_csv_tuple() for row in first_five] == [
        item.as_csv_tuple() for item in HANTAVIRIDAE_SPOT_CHECKS
    ]


def test_alkhumra_is_its_own_orthoflavivirus_row(parsed_records: tuple) -> None:
    flavi = [row for row in parsed_records if row.genus == "Orthoflavivirus"]
    names = [row.virus for row in flavi]
    assert "Absettarov virus" in names
    assert "Alkhumra haemorrhagic fever virus" in names
    assert all(
        "Alkhumra" not in name or name == "Alkhumra haemorrhagic fever virus" for name in names
    )


def test_louping_ill_keeps_asterisk_on_hazard_group(parsed_records: tuple) -> None:
    match = next(row for row in parsed_records if row.virus == "Louping ill virus")
    assert match.hazard_group == "3*"
    assert match.schedule_5 == ""
