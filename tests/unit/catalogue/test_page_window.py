"""Page 27–42 window and Annex 1 halt. Primary stop is the printed-page range."""

from __future__ import annotations

from virus_redteaming.catalogue.page_window import (
    AnnexTitleHaltPolicy,
    PageDecision,
    PrintedPageWindow,
    VirusSectionPageSelector,
)
from virus_redteaming.catalogue.paths import (
    APPROVED_LIST_PDF_FILENAME,
    CatalogueOutputPath,
    CatalogueSourcePath,
    DOCS_DIRECTORY_NAME,
    OUTPUT_DIRECTORY_NAME,
    VIRUS_CSV_FILENAME,
)


def test_window_is_printed_pages_27_through_42_inclusive() -> None:
    window = PrintedPageWindow()
    assert window.contains(26) is False
    assert window.contains(27) is True
    assert window.contains(42) is True
    assert window.contains(43) is False


def test_selector_includes_27_and_42_and_halts_43() -> None:
    selector = VirusSectionPageSelector()
    virus_page = "Health and Safety Executive\nFamily Togaviridae\nOther alphaviruses known to be pathogenic in humans 2"
    annex_page = (
        "Health and Safety Executive\n"
        "Annex 1: Biological agents which may be used at less "
        "than the minimum containment conditions"
    )
    assert selector.decide(27, virus_page) is PageDecision.INCLUDE
    assert selector.decide(42, virus_page) is PageDecision.INCLUDE
    assert selector.decide(43, annex_page) is PageDecision.HALT
    assert selector.decide(43, virus_page) is PageDecision.HALT


def test_hse_header_alone_does_not_halt_a_virus_table_page() -> None:
    policy = AnnexTitleHaltPolicy()
    assert policy.should_halt("Health and Safety Executive\nGenus Alphavirus") is False
    assert (
        policy.should_halt(
            "Health and Safety Executive\n"
            "Annex 1: Biological agents which may be used at less "
            "than the minimum containment conditions"
        )
        is True
    )


def test_default_pdf_path_is_docs_misc208() -> None:
    path = CatalogueSourcePath().resolve()
    assert path.name == APPROVED_LIST_PDF_FILENAME
    assert path.parent.name == DOCS_DIRECTORY_NAME


def test_default_csv_path_is_output_viruses_csv() -> None:
    path = CatalogueOutputPath().resolve()
    assert path.name == VIRUS_CSV_FILENAME
    assert path.parent.name == OUTPUT_DIRECTORY_NAME
