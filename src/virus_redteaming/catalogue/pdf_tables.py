"""pdfplumber adapter. The only type that may import the PDF library."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from virus_redteaming.catalogue.errors import CatalogueParseError
from virus_redteaming.catalogue.models import TableRow
from virus_redteaming.catalogue.page_window import (
    PageDecision,
    VirusSectionPageSelector,
)


class PdfPlumberTableExtractor:
    def __init__(self, selector: VirusSectionPageSelector | None = None) -> None:
        self._selector = selector or VirusSectionPageSelector()

    def extract(self, pdf_path: Path) -> Sequence[TableRow]:
        try:
            import pdfplumber
        except ImportError as exc:  # pragma: no cover - environment
            raise CatalogueParseError("pdfplumber is required to read the Approved List PDF.") from exc
        if not pdf_path.is_file():
            raise CatalogueParseError(f"PDF not found: {pdf_path}")
        rows: list[TableRow] = []
        with pdfplumber.open(pdf_path) as pdf:
            for index, page in enumerate(pdf.pages):
                printed_page = index + 1
                page_text = page.extract_text() or ""
                if self._selector.decide(printed_page, page_text) is PageDecision.HALT:
                    if printed_page < self._selector.window.start:
                        continue
                    break
                for table in page.extract_tables() or []:
                    for raw in table:
                        rows.append(self._to_row(raw, printed_page))
        return tuple(rows)

    def _to_row(self, raw: list[str | None] | tuple[str | None, ...], printed_page: int) -> TableRow:
        cells = [(cell or "") for cell in raw]
        while len(cells) < 3:
            cells.append("")
        return TableRow(
            agent=cells[0],
            hazard_group=cells[1],
            notes=cells[2],
            printed_page=printed_page,
        )
