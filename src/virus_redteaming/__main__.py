"""Thin CLI. Assembles the object graph; contains no parse rules."""

from __future__ import annotations

import argparse
import sys
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
from virus_redteaming.claude_harness.config import ClaudeApiConfig
from virus_redteaming.clinical_fasta.biopython_entrez import BiopythonEntrezClient
from virus_redteaming.clinical_fasta.errors import NcbiConfigError
from virus_redteaming.clinical_fasta.fasta_encoder import BiopythonFastaEncoder
from virus_redteaming.clinical_fasta.fasta_source import (
    AccessionIdentity,
    FastaFetchSource,
)
from virus_redteaming.clinical_fasta.sink import AtomicPathFastaSink
from virus_redteaming.core.errors import VirusRedteamingError
from virus_redteaming.hse_cat1_merge.io import (
    Cat1CsvReader,
    HseCsvReader,
    MergedCsvWriter,
    VmrTaxonReader,
)
from virus_redteaming.hse_cat1_merge.order import MergedTableOrder
from virus_redteaming.hse_cat1_merge.workflow import MergeHseAndCat1
from virus_redteaming.ncbi_fasta.cache import DirectoryFastaCache
from virus_redteaming.ncbi_fasta.config import entrez_config_from_environment
from virus_redteaming.ncbi_fasta.models import FetchNcbiFastaReport
from virus_redteaming.ncbi_fasta.parse import GenBankSegmentParser
from virus_redteaming.ncbi_fasta.source import MergedGenBankSource
from virus_redteaming.ncbi_fasta.workflow import NcbiFastaDownload
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
    fetch = sub.add_parser(
        "fetch-ncbi-fasta",
        help="Download FASTA for GenBank accessions in the merged table",
    )
    fetch.add_argument(
        "--csv",
        type=Path,
        default=Path("output/HSE-virus_Cat1-virus_merged.csv"),
        help="Merged table (default: output/HSE-virus_Cat1-virus_merged.csv)",
    )
    fetch.add_argument(
        "--out",
        type=Path,
        default=Path("output/NCBI_fasta"),
        help="FASTA directory (default: output/NCBI_fasta)",
    )
    red_team = sub.add_parser(
        "claude-red-team",
        help="Send prepared FASTA files to Claude and write the response CSV",
    )
    red_team.add_argument(
        "--csv",
        type=Path,
        default=Path("output/HSE-virus_Cat1-virus_merged.csv"),
        help="Merged table (default: output/HSE-virus_Cat1-virus_merged.csv)",
    )
    red_team.add_argument(
        "--fasta",
        type=Path,
        default=Path("output/NCBI_fasta"),
        help="FASTA directory (default: output/NCBI_fasta)",
    )
    red_team.add_argument(
        "--out",
        type=Path,
        default=Path("output/claude_red-team_response.csv"),
        help="Response CSV (default: output/claude_red-team_response.csv)",
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
    if args.command == "fetch-ncbi-fasta":
        return _print_ncbi_fasta(args.csv, args.out)
    if args.command == "claude-red-team":
        return _print_claude_red_team(args.csv, args.fasta, args.out)
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


def _print_ncbi_fasta(csv_path: Path, out_dir: Path) -> int:
    try:
        report = _fetch_ncbi_fasta(csv_path, out_dir)
    except NcbiConfigError as exc:
        print(exc, file=sys.stderr)
        return 2
    except VirusRedteamingError as exc:
        print(exc, file=sys.stderr)
        return 1
    for path in report.written:
        print(path)
    print(f"skipped {report.blank_rows} blank rows")
    print(f"cached {len(report.cached)} accessions")
    print(f"fetched {len(report.written)} accessions")
    return 0


def _fetch_ncbi_fasta(csv_path: Path, out_dir: Path) -> FetchNcbiFastaReport:
    identity = AccessionIdentity()
    client = BiopythonEntrezClient(entrez_config_from_environment())
    return NcbiFastaDownload(
        source=MergedGenBankSource(csv_path, GenBankSegmentParser()),
        cache=DirectoryFastaCache(out_dir, identity),
        records=FastaFetchSource(client, identity),
        encoder=BiopythonFastaEncoder(),
        sink=AtomicPathFastaSink(out_dir),
    ).run()


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


def _print_claude_red_team(csv_path: Path, fasta_dir: Path, out_path: Path) -> int:
    from dotenv import load_dotenv

    from virus_redteaming.claude_harness.config import ClaudeApiConfig
    from virus_redteaming.claude_harness.errors import (
        MissingClaudeApiKeyError,
        redact_client_error,
    )
    from virus_redteaming.core.errors import VirusRedteamingError

    load_dotenv(override=True)
    try:
        config = ClaudeApiConfig.from_environment()
    except MissingClaudeApiKeyError as exc:
        print(exc, file=sys.stderr)
        return 2
    try:
        _run_claude_red_team(config, csv_path, fasta_dir, out_path)
    except VirusRedteamingError as exc:
        print(redact_client_error(exc), file=sys.stderr)
        return 1
    return 0


def _run_claude_red_team(
    config: ClaudeApiConfig,
    csv_path: Path,
    fasta_dir: Path,
    out_path: Path,
) -> None:
    from virus_redteaming.claude_harness.anthropic_chat import AnthropicChat
    from virus_redteaming.claude_harness.layers import HarnessLayer
    from virus_redteaming.claude_harness.prompt import SequencePrompt
    from virus_redteaming.claude_harness.sequence import FastaSequence
    from virus_redteaming.claude_harness.sink import RedTeamReportWriter
    from virus_redteaming.claude_harness.source import MergedRedTeamSource
    from virus_redteaming.claude_harness.timed_chat import TimedChat
    from virus_redteaming.claude_harness.upload import SequenceUpload
    from virus_redteaming.claude_harness.workflow import (
        ClaudePing,
        RedTeamBatch,
        RedTeamExchange,
    )

    chat = AnthropicChat(config, timeout=180.0, max_tokens=4096)
    ping = ClaudePing(TimedChat(chat))
    RedTeamBatch(
        source=MergedRedTeamSource(csv_path),
        fasta=FastaSequence(fasta_dir),
        exchange=RedTeamExchange(
            ping,
            SequenceUpload(config, fasta_dir),
            SequencePrompt(),
            fasta_dir,
        ),
        writer=RedTeamReportWriter(out_path),
        width=HarnessLayer.LIVE.chain_count(),
    ).run()


if __name__ == "__main__":
    raise SystemExit(main())
