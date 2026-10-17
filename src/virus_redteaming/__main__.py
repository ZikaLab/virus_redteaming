"""Thin CLI. Assembles the object graph; contains no parse rules."""

from __future__ import annotations

import argparse
from pathlib import Path

from virus_redteaming.catalogue.csv_sink import LongFormatCsvWriter
from virus_redteaming.catalogue.parser import ApprovedVirusListParser
from virus_redteaming.catalogue.paths import (
    SCHEDULE5_UNMATCHED_FILENAME,
    CatalogueOutputPath,
    CatalogueSourcePath,
    Schedule5ListPath,
)
from virus_redteaming.catalogue.pdf_tables import PdfPlumberTableExtractor
from virus_redteaming.catalogue.schedule5_annotate import (
    AnnotateSchedule5,
    CatalogueCsvReader,
    Schedule5CsvAnnotator,
    Schedule5CsvWriter,
    UnmatchedNameSink,
)
from virus_redteaming.catalogue.schedule5_match import VirusNameInteractor, VirusNameNormaliser
from virus_redteaming.catalogue.schedule5_source import MarkdownBulletNameSource
from virus_redteaming.catalogue.workflow import ParseApprovedVirusList


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="virus_redteaming")
    sub = parser.add_subparsers(dest="command", required=True)
    parse_viruses = sub.add_parser(
        "parse-viruses",
        help="Parse the Approved List virus tables to long-format CSV",
    )
    parse_viruses.add_argument(
        "--pdf",
        type=Path,
        default=CatalogueSourcePath().resolve(),
        help="Approved List PDF (default: docs/misc208.pdf)",
    )
    parse_viruses.add_argument(
        "--out",
        type=Path,
        default=CatalogueOutputPath().resolve(),
        help="CSV path (default: output/viruses.csv)",
    )
    annotate = sub.add_parser(
        "annotate-schedule-5",
        help="Mark Schedule 5 on the virus catalogue from docs/schedule5.md",
    )
    annotate.add_argument(
        "--list",
        type=Path,
        default=Schedule5ListPath().resolve(),
        help="Schedule 5 name list (default: docs/schedule5.md)",
    )
    annotate.add_argument(
        "--csv",
        type=Path,
        default=CatalogueOutputPath().resolve(),
        help="Catalogue CSV (default: output/viruses.csv)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "parse-viruses":
        count = ParseApprovedVirusList(
            extractor=PdfPlumberTableExtractor(),
            parser=ApprovedVirusListParser(),
            sink=LongFormatCsvWriter(args.out),
        ).run(args.pdf)
        print(f"wrote {count} rows to {args.out}")
        return 0
    if args.command == "annotate-schedule-5":
        result = _annotate_schedule5().run(
            args.list,
            args.csv,
            args.csv.parent / SCHEDULE5_UNMATCHED_FILENAME,
        )
        print(
            f"annotated {len(result.rows)} rows; "
            f"{len(result.matched_names)} schedule 5 names matched"
        )
        return 0
    raise SystemExit(2)


def _annotate_schedule5() -> AnnotateSchedule5:
    return AnnotateSchedule5(
        source=MarkdownBulletNameSource(),
        reader=CatalogueCsvReader(),
        annotator=Schedule5CsvAnnotator(VirusNameInteractor(VirusNameNormaliser())),
        writer=Schedule5CsvWriter(),
        unmatched_sink=UnmatchedNameSink(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
