"""Default source and artefact locations. One reason to change: directory layout."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DOCS_DIRECTORY_NAME = "docs"
APPROVED_LIST_PDF_FILENAME = "misc208.pdf"
SCHEDULE5_LIST_FILENAME = "schedule5.md"
OUTPUT_DIRECTORY_NAME = "output"
VIRUS_CSV_FILENAME = "viruses.csv"
SCHEDULE5_UNMATCHED_FILENAME = "schedule5_unmatched.txt"


@dataclass(frozen=True)
class CatalogueSourcePath:
    """Source PDFs for parse-viruses: docs/misc208.pdf under the process working directory."""

    directory_name: str = DOCS_DIRECTORY_NAME
    filename: str = APPROVED_LIST_PDF_FILENAME

    def resolve(self, root: Path | None = None) -> Path:
        base = root if root is not None else Path.cwd()
        return base / self.directory_name / self.filename


@dataclass(frozen=True)
class Schedule5ListPath:
    """Schedule 5 name list: docs/schedule5.md under the process working directory."""

    directory_name: str = DOCS_DIRECTORY_NAME
    filename: str = SCHEDULE5_LIST_FILENAME

    def resolve(self, root: Path | None = None) -> Path:
        base = root if root is not None else Path.cwd()
        return base / self.directory_name / self.filename


@dataclass(frozen=True)
class CatalogueOutputPath:
    """Standard generated CSV: output/viruses.csv under the process working directory."""

    directory_name: str = OUTPUT_DIRECTORY_NAME
    filename: str = VIRUS_CSV_FILENAME

    def resolve(self, root: Path | None = None) -> Path:
        base = root if root is not None else Path.cwd()
        return base / self.directory_name / self.filename
