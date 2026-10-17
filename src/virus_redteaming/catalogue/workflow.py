"""Orchestrate extractor → parser → CSV sink."""

from __future__ import annotations

from pathlib import Path

from virus_redteaming.catalogue.parser import ApprovedVirusListParser
from virus_redteaming.catalogue.protocols import RecordSink, TableExtractor


class ParseApprovedVirusList:
    def __init__(
        self,
        extractor: TableExtractor,
        parser: ApprovedVirusListParser,
        sink: RecordSink,
    ) -> None:
        self._extractor = extractor
        self._parser = parser
        self._sink = sink

    def run(self, pdf_path: Path) -> int:
        rows = self._extractor.extract(pdf_path)
        records = self._parser.parse(rows)
        self._sink.write(records)
        return len(records)
