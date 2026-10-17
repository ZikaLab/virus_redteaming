"""Annotate catalogue rows with Schedule 5 membership. Does not parse PDFs."""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Sequence

from virus_redteaming.catalogue.errors import CatalogueParseError
from virus_redteaming.catalogue.schedule5_match import VirusNameInteractor
from virus_redteaming.catalogue.schedule5_source import Schedule5NameSource

SCHEDULE_5_HEADER = "Schedule 5"
_ACCEPTED_SCHEDULE_HEADERS = frozenset({"schedule 5"})
_STABLE_HEADERS = ("Family", "Genus", "Virus", "Human pathogen hazard group")


@dataclass(frozen=True)
class CatalogueRow:
    family: str
    genus: str
    virus: str
    hazard_group: str
    schedule_5: str


@dataclass(frozen=True)
class AnnotationResult:
    rows: tuple[CatalogueRow, ...]
    matched_names: frozenset[str]
    unmatched_names: tuple[str, ...]


class CatalogueCsvReader:
    def read(self, path: Path) -> tuple[CatalogueRow, ...]:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            schedule_key = self._schedule_key(reader.fieldnames)
            rows: list[CatalogueRow] = []
            for raw in reader:
                rows.append(
                    CatalogueRow(
                        family=raw["Family"],
                        genus=raw["Genus"],
                        virus=raw["Virus"],
                        hazard_group=raw["Human pathogen hazard group"],
                        schedule_5=raw[schedule_key],
                    )
                )
        return tuple(rows)

    def _schedule_key(self, fieldnames: Sequence[str] | None) -> str:
        if fieldnames is None or any(header not in fieldnames for header in _STABLE_HEADERS):
            raise CatalogueParseError("Catalogue CSV is missing a required column.")
        for field in fieldnames:
            if field.strip().casefold() in _ACCEPTED_SCHEDULE_HEADERS:
                return field
        raise CatalogueParseError("Catalogue CSV is missing the Schedule 5 column.")


class Schedule5CsvWriter:
    def write(self, path: Path, rows: Sequence[CatalogueRow]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow((*_STABLE_HEADERS, SCHEDULE_5_HEADER))
            for row in rows:
                writer.writerow(
                    (row.family, row.genus, row.virus, row.hazard_group, row.schedule_5)
                )


class UnmatchedNameSink:
    def write(self, path: Path, names: Sequence[str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not names:
            path.write_bytes(b"")
            return
        lines = "\n".join(sorted(names)) + "\n"
        path.write_text(lines, encoding="utf-8")


class Schedule5CsvAnnotator:
    def __init__(self, interactor: VirusNameInteractor) -> None:
        self._interactor = interactor

    def annotate(
        self,
        original_rows: Sequence[CatalogueRow],
        schedule_names: Sequence[str],
    ) -> AnnotationResult:
        names = tuple(schedule_names)
        updated: list[CatalogueRow] = []
        used: set[str] = set()
        for row in original_rows:
            hits = self._interactor.matched_names(row.virus, names)
            used.update(hits)
            updated.append(replace(row, schedule_5="1" if hits else "0"))
        unmatched = tuple(sorted(name for name in names if name not in used))
        return AnnotationResult(tuple(updated), frozenset(used), unmatched)


class AnnotateSchedule5:
    def __init__(
        self,
        source: Schedule5NameSource,
        reader: CatalogueCsvReader,
        annotator: Schedule5CsvAnnotator,
        writer: Schedule5CsvWriter,
        unmatched_sink: UnmatchedNameSink,
    ) -> None:
        self._source = source
        self._reader = reader
        self._annotator = annotator
        self._writer = writer
        self._unmatched_sink = unmatched_sink

    def run(self, list_path: Path, csv_path: Path, unmatched_path: Path) -> AnnotationResult:
        names = self._source.load(list_path)
        original = self._reader.read(csv_path)
        result = self._annotator.annotate(original, names)
        self._unmatched_sink.write(unmatched_path, result.unmatched_names)
        self._writer.write(csv_path, result.rows)
        return result
