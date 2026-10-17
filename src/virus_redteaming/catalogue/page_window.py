"""Where the virus tables live in misc208.pdf. One reason to change: page bounds."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from virus_redteaming.catalogue.text import collapse_whitespace

VIRUS_SECTION_START_PAGE = 27
VIRUS_SECTION_END_PAGE = 42

ANNEX_1_TITLE = (
    "annex 1: biological agents which may be used at less "
    "than the minimum containment conditions"
)
HSE_HEADER = "health and safety executive"


@dataclass(frozen=True)
class PrintedPageWindow:
    """Inclusive printed-page range. misc208 virus tables are 27..42."""

    start: int = VIRUS_SECTION_START_PAGE
    end: int = VIRUS_SECTION_END_PAGE

    def contains(self, printed_page: int) -> bool:
        return self.start <= printed_page <= self.end


class PageDecision(Enum):
    INCLUDE = "include"
    HALT = "halt"


class PageHaltPolicy(Protocol):
    def should_halt(self, page_text: str) -> bool:
        """Return True if this page must not be extracted."""


class AnnexTitleHaltPolicy:
    """Halt when a page is Annex 1, not when it merely says Health and Safety Executive.

    Every Approved List page prints the HSE header. Only page 43+ pairs that
    header with the Annex 1 title. That pairing is the stop signal if a caller
    ever asks about a page after 42.
    """

    def should_halt(self, page_text: str) -> bool:
        collapsed = collapse_whitespace(page_text).casefold()
        return HSE_HEADER in collapsed and ANNEX_1_TITLE in collapsed


class VirusSectionPageSelector:
    """Decide INCLUDE vs HALT for one printed page (open/closed: swap the policy)."""

    def __init__(
        self,
        window: PrintedPageWindow | None = None,
        annex_halt: PageHaltPolicy | None = None,
    ) -> None:
        self._window = window or PrintedPageWindow()
        self._annex_halt = annex_halt or AnnexTitleHaltPolicy()

    @property
    def window(self) -> PrintedPageWindow:
        return self._window

    def decide(self, printed_page: int, page_text: str) -> PageDecision:
        if not self._window.contains(printed_page):
            return PageDecision.HALT
        if self._annex_halt.should_halt(page_text):
            return PageDecision.HALT
        return PageDecision.INCLUDE
