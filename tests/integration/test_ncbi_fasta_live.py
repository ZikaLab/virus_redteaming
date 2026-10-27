"""Opt-in NCBI call. Skipped unless NCBI_LIVE_TEST=1 and NCBI_EMAIL are both set."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from virus_redteaming.clinical_fasta.biopython_entrez import BiopythonEntrezClient
from virus_redteaming.clinical_fasta.fasta_encoder import BiopythonFastaEncoder
from virus_redteaming.clinical_fasta.fasta_source import (
    AccessionIdentity,
    FastaFetchSource,
)
from virus_redteaming.clinical_fasta.sink import AtomicPathFastaSink
from virus_redteaming.ncbi_fasta.cache import DirectoryFastaCache
from virus_redteaming.ncbi_fasta.config import entrez_config_from_environment
from virus_redteaming.ncbi_fasta.parse import GenBankSegmentParser
from virus_redteaming.ncbi_fasta.source import MergedGenBankSource
from virus_redteaming.ncbi_fasta.workflow import NcbiFastaDownload

pytestmark = pytest.mark.network


def _live_enabled() -> bool:
    email = os.environ.get("NCBI_EMAIL", "")
    return os.environ.get("NCBI_LIVE_TEST") == "1" and bool(email) and not any(
        character.isspace() for character in email
    )


def test_live_v00603_writes_versioned_header(tmp_path: Path) -> None:
    if not _live_enabled():
        pytest.skip("NCBI live test requires NCBI_LIVE_TEST=1 and NCBI_EMAIL")
    table = tmp_path / "one.csv"
    table.write_text("GenBank accessions\nV00603\n", encoding="utf-8")
    out = tmp_path / "fasta"
    identity = AccessionIdentity()
    report = NcbiFastaDownload(
        source=MergedGenBankSource(table, GenBankSegmentParser()),
        cache=DirectoryFastaCache(out, identity),
        records=FastaFetchSource(
            BiopythonEntrezClient(entrez_config_from_environment()),
            identity,
        ),
        encoder=BiopythonFastaEncoder(),
        sink=AtomicPathFastaSink(out),
    ).run()
    written = out / "V00603.fasta"
    assert report.written == (written,)
    assert written.read_text(encoding="utf-8").startswith(">V00603.1")
