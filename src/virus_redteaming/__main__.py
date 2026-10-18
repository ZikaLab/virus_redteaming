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
from virus_redteaming.catalogue.schedule5_match import (
    VirusNameInteractor,
    VirusNameNormaliser,
)
from virus_redteaming.catalogue.schedule5_source import MarkdownBulletNameSource
from virus_redteaming.catalogue.workflow import ParseApprovedVirusList
from virus_redteaming.category1.except_sample import (
    GenusCategory1Sampler,
    GenusVirusExcept,
)
from virus_redteaming.category1.inventory import CatalogueGenusIndex
from virus_redteaming.category1.workflow import BuildCategory1
from virus_redteaming.category1.write import IctvCat1Writer, NenReader, NenWriter
from virus_redteaming.hse_cat1_merge.io import (
    Cat1CsvReader,
    HseCsvReader,
    MergedCsvWriter,
    VmrTaxonReader,
)
from virus_redteaming.hse_cat1_merge.order import MergedTableOrder
from virus_redteaming.hse_cat1_merge.workflow import MergeHseAndCat1
from virus_redteaming.nen_accession.index import ExemplarIndexFactory
from virus_redteaming.nen_accession.io import (
    NenAccessionWriter,
    NenCsvReader,
    VmrCsvReader,
)
from virus_redteaming.nen_accession.parse import GenBankAccessionParser
from virus_redteaming.nen_accession.workflow import AssignNenAccessions


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
    category1 = sub.add_parser(
        "category1",
        help="Sample Category 1 ICTV rows from an existing nen_viruses.csv",
    )
    category1.add_argument("--viruses", type=Path, default=Path("output/viruses.csv"))
    category1.add_argument(
        "--ictv",
        type=Path,
        default=Path("docs/ICTV_RNA_virus_species_MSL41.csv"),
    )
    category1.add_argument("--nen", type=Path, default=Path("output/nen_viruses.csv"))
    category1.add_argument("--out", type=Path, default=Path("output/ICTV_cat1.csv"))
    category1.add_argument(
        "--refresh",
        action="store_true",
        help="Re-run prompts. The CLI has none and raises Category1PromptRequired.",
    )
    accessions = sub.add_parser(
        "assign-nen-accessions",
        help="Copy VMR GenBank accessions onto NEN virus rows",
    )
    accessions.add_argument("--nen", type=Path, default=Path("output/nen_viruses.csv"))
    accessions.add_argument(
        "--vmr",
        type=Path,
        default=Path("docs/VMR_MSL41.v1.20260729.csv"),
    )
    merge = sub.add_parser(
        "merge-hse-cat1",
        help="Stack the HSE and Category 1 tables, then sort the published file",
    )
    merge.add_argument("--nen", type=Path, default=Path("output/nen_viruses.csv"))
    merge.add_argument("--cat1", type=Path, default=Path("output/ICTV_cat1.csv"))
    merge.add_argument(
        "--vmr",
        type=Path,
        default=Path("docs/VMR_MSL41.v1.20260729.csv"),
    )
    merge.add_argument(
        "--out",
        type=Path,
        default=Path("output/HSE-virus_Cat1-virus_merged.csv"),
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
    if args.command == "category1":
        _build_category1().run(
            args.viruses,
            args.ictv,
            args.nen,
            args.out,
            refresh=args.refresh,
        )
        print(f"wrote {args.out}")
        return 0
    if args.command == "assign-nen-accessions":
        report = _assign_nen_accessions().run(args.nen, args.vmr)
        print(f"matched {report.matched} rows")
        for name in report.unmatched_names:
            print(f"unmatched NEN virus: {name}")
        print(f"blank NEN virus: {report.blank_nen_virus}")
        return 0
    if args.command == "merge-hse-cat1":
        count = _merge_hse_cat1().run(args.nen, args.cat1, args.vmr, args.out)
        print(f"wrote {count} rows to {args.out}")
        return 0
    raise SystemExit(2)


def _build_category1() -> BuildCategory1:
    return BuildCategory1(
        catalogue_index=CatalogueGenusIndex(),
        harmonizer=None,
        exceptor=GenusVirusExcept(),
        sampler=GenusCategory1Sampler(),
        nen_writer=NenWriter(),
        nen_reader=NenReader(),
        cat1_writer=IctvCat1Writer(),
    )


def _assign_nen_accessions() -> AssignNenAccessions:
    return AssignNenAccessions(
        vmr_reader=VmrCsvReader(),
        nen_reader=NenCsvReader(),
        writer=NenAccessionWriter(),
        parser=GenBankAccessionParser(),
        index_factory=ExemplarIndexFactory(),
    )


def _merge_hse_cat1() -> MergeHseAndCat1:
    return MergeHseAndCat1(
        hse_reader=HseCsvReader(),
        cat1_reader=Cat1CsvReader(),
        vmr_reader=VmrTaxonReader(),
        writer=MergedCsvWriter(),
        parser=GenBankAccessionParser(),
        order=MergedTableOrder(),
    )


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
