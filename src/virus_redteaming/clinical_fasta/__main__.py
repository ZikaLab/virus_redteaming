"""Assemble the clinical FASTA object graph. This module holds no search phrase."""

import argparse
import sys
from pathlib import Path

from virus_redteaming.clinical_fasta.accession_list import AccessionList
from virus_redteaming.clinical_fasta.accession_sink import AtomicAccessionTableSink
from virus_redteaming.clinical_fasta.accession_source import (
    AccessionCsvSource,
    AccessionHitCsvSource,
)
from virus_redteaming.clinical_fasta.biopython_entrez import BiopythonEntrezClient
from virus_redteaming.clinical_fasta.config import NcbiEntrezConfig
from virus_redteaming.clinical_fasta.criteria_representatives import (
    CriteriaRepresentativeFiles,
)
from virus_redteaming.clinical_fasta.criteria_sink import AtomicCriteriaSink
from virus_redteaming.clinical_fasta.csv_source import OutputCsvVirusSource
from virus_redteaming.clinical_fasta.download_workflow import ClinicalFastaDownload
from virus_redteaming.clinical_fasta.errors import ClinicalFastaError, NcbiConfigError
from virus_redteaming.clinical_fasta.fasta_encoder import BiopythonFastaEncoder
from virus_redteaming.clinical_fasta.fasta_measure import FastaMeasure
from virus_redteaming.clinical_fasta.fasta_source import (
    AccessionIdentity,
    FastaFetchSource,
)
from virus_redteaming.clinical_fasta.genes_align import AtomicGenesAligner
from virus_redteaming.clinical_fasta.header_match import HeaderMatch
from virus_redteaming.clinical_fasta.length import LengthCutoff
from virus_redteaming.clinical_fasta.models import SearchResult
from virus_redteaming.clinical_fasta.parse_workflow import RepresentativeParse
from virus_redteaming.clinical_fasta.paths import (
    ACCESSION_FILENAME,
    CRITERIA_FILENAME,
    DEFAULT_QUERY_FILENAME,
    FASTA_DIRECTORY_NAME,
    OUTPUT_DIRECTORY_NAME,
    REPRESENTATIVE_FILENAME,
    SEARCH_TERM_FILENAME,
    OutputCsvPath,
)
from virus_redteaming.clinical_fasta.representative_selection import (
    RepresentativeSelection,
)
from virus_redteaming.clinical_fasta.representative_sink import AtomicRepresentativeSink
from virus_redteaming.clinical_fasta.screened_words import ScreenedWords
from virus_redteaming.clinical_fasta.search_term import OutputSearchTermSource
from virus_redteaming.clinical_fasta.search_workflow import AccessionSearch
from virus_redteaming.clinical_fasta.sink import AtomicPathFastaSink
from virus_redteaming.clinical_fasta.term import EntrezTermComposer


def main(argv: list[str] | None = None) -> int:
    """Run search, download, or parse.

    ``LengthCutoff.DEFAULT_BP`` and ``LengthCutoff.MAX_SLEN`` live in ``length.py``.
    ``--min-length`` overrides ``DEFAULT_BP`` for one run and does not edit it.
    """
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "parse":
            for path in _parse():
                print(path)
            return 0
        cutoff = _cutoff(args.min_length)
        if args.command == "search":
            result = _search(args.filename, cutoff)
            print(result.path)
            for virus in result.misses:
                print(f"no accessions for Virus cell: {virus}", file=sys.stderr)
            if result.misses:
                return 1
        else:
            for path in _download(cutoff):
                print(path)
    except NcbiConfigError as exc:
        print(exc, file=sys.stderr)
        return 2
    except ClinicalFastaError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="virus_redteaming.clinical_fasta")
    subcommands = parser.add_subparsers(dest="command", required=True)
    search = subcommands.add_parser("search")
    search.add_argument("filename", nargs="?", default=DEFAULT_QUERY_FILENAME)
    search.add_argument("--min-length", type=int, default=None)
    download = subcommands.add_parser("download")
    download.add_argument("--min-length", type=int, default=None)
    subcommands.add_parser("parse")
    return parser


def _cutoff(min_length: int | None) -> LengthCutoff:
    if min_length is None:
        return LengthCutoff()
    if min_length < 0:
        raise NcbiConfigError("--min-length must be an integer of 0 or greater")
    return LengthCutoff(bp=min_length)


def _search(filename: str, cutoff: LengthCutoff) -> SearchResult:
    root = Path.cwd()
    query = OutputCsvPath(filename).resolve(root)
    workflow = AccessionSearch(
        viruses=OutputCsvVirusSource(query),
        extra_term=OutputSearchTermSource(
            root / OUTPUT_DIRECTORY_NAME / SEARCH_TERM_FILENAME
        ),
        composer=EntrezTermComposer(),
        searcher=BiopythonEntrezClient(NcbiEntrezConfig.from_environment()),
        accession_list=AccessionList(),
        cutoff=cutoff,
        sink=AtomicAccessionTableSink(
            root / OUTPUT_DIRECTORY_NAME / ACCESSION_FILENAME
        ),
    )
    return workflow.run()


def _parse() -> tuple[Path, Path, Path]:
    root = Path.cwd()
    output = root / OUTPUT_DIRECTORY_NAME
    workflow = RepresentativeParse(
        group_source=AccessionHitCsvSource(output / ACCESSION_FILENAME),
        fasta_directory=output / FASTA_DIRECTORY_NAME,
        screened_words=ScreenedWords(),
        measure=FastaMeasure(),
        match=HeaderMatch(),
        selection=RepresentativeSelection(),
        criteria_sink=AtomicCriteriaSink(output / CRITERIA_FILENAME),
        representative_sink=AtomicRepresentativeSink(output / REPRESENTATIVE_FILENAME),
        representative_source=CriteriaRepresentativeFiles(),
        genes_aligner=AtomicGenesAligner(output / DEFAULT_QUERY_FILENAME),
    )
    return workflow.run()


def _download(cutoff: LengthCutoff) -> tuple[Path, ...]:
    root = Path.cwd()
    workflow = ClinicalFastaDownload(
        accessions=AccessionCsvSource(
            root / OUTPUT_DIRECTORY_NAME / ACCESSION_FILENAME
        ),
        source=FastaFetchSource(
            BiopythonEntrezClient(NcbiEntrezConfig.from_environment()),
            AccessionIdentity(),
        ),
        cutoff=cutoff,
        encoder=BiopythonFastaEncoder(),
        sink=AtomicPathFastaSink(root / OUTPUT_DIRECTORY_NAME / FASTA_DIRECTORY_NAME),
    )
    return workflow.run()


if __name__ == "__main__":
    raise SystemExit(main())
