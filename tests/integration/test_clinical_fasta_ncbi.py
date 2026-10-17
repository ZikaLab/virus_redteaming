"""Opt-in NCBI call. Skipped unless NCBI_LIVE_TEST=1 and NCBI_EMAIL are both set."""

from __future__ import annotations

import csv
import os
from collections import Counter
from pathlib import Path

import pytest
from tests.conftest import REPO_ROOT

from virus_redteaming.clinical_fasta.__main__ import main
from virus_redteaming.clinical_fasta.length import LengthCutoff

pytestmark = pytest.mark.network


def _live_enabled() -> bool:
    email = os.environ.get("NCBI_EMAIL", "")
    return os.environ.get("NCBI_LIVE_TEST") == "1" and bool(email) and not any(
        character.isspace() for character in email
    )


@pytest.mark.network
def test_live_search_then_download() -> None:
    """Search, then download, using only the CSV and search.txt on disk."""
    if not _live_enabled():
        pytest.skip("NCBI live test requires NCBI_LIVE_TEST=1 and NCBI_EMAIL")
    output = REPO_ROOT / "output"
    if not (output / "genes.csv").is_file() or not (output / "search.txt").is_file():
        pytest.fail("output/genes.csv and output/search.txt are required")
    previous = Path.cwd()
    os.chdir(REPO_ROOT)
    try:
        assert main(["search"]) in (0, 1)
        table = output / "accessions.csv"
        with table.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert rows
        counts = Counter(row["Virus"] for row in rows)
        assert counts
        assert all(count <= 5 for count in counts.values())
        accessions = [row["Accession"] for row in rows]
        assert main(["download"]) == 0
    finally:
        os.chdir(previous)
    directory = output / "clinical_genes"
    written = [directory / f"{accession}.fasta" for accession in accessions]
    assert all(path.is_file() for path in written)
    for path in written:
        sequence = "".join(
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith(">")
        )
        assert len(sequence) > LengthCutoff.DEFAULT_BP
