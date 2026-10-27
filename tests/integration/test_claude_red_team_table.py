"""The real merged table selects 393 rows and only the first accession of each cell."""

import csv
from pathlib import Path

import pytest

from virus_redteaming.claude_harness.prompt import SequencePrompt
from virus_redteaming.claude_harness.sequence import FastaSequence
from virus_redteaming.claude_harness.source import MergedRedTeamSource

_REPO = Path(__file__).resolve().parents[2]
_TABLE = _REPO / "output" / "HSE-virus_Cat1-virus_merged.csv"
_FASTA = _REPO / "output" / "NCBI_fasta"


def test_merged_table_selects_first_codes_only(tmp_path: Path) -> None:
    if not _TABLE.is_file():
        pytest.skip("merged table is not in the workspace")
    rows = MergedRedTeamSource(_TABLE).read()
    assert len(rows) == 393
    flu = [row for row in rows if row.virus == "influenza A virus"]
    assert flu
    assert {row.accession for row in flu} == {"V00603"}
    prompts = SequencePrompt()
    text = prompts.count() + prompts.structure()
    for value in ("influenza A virus", "Orthomyxoviridae", "Alphainfluenzavirus"):
        assert value not in text
    created: list[Path] = []
    try:
        for row in rows:
            if row.accession == "":
                continue
            fasta = _FASTA / f"{row.accession}.fasta"
            assert fasta.is_file(), row.accession
            prepared = FastaSequence(_FASTA, tmp_path).prepare(row.accession)
            assert prepared is not None
            created.append(prepared)
            body = prepared.read_bytes()
            assert b"influenza A virus" not in body
            assert not body.startswith(b">")
    finally:
        for path in created:
            path.unlink(missing_ok=True)
            path.with_suffix(".txt.writing").unlink(missing_ok=True)


def test_output_header_matches_the_spec(tmp_path: Path) -> None:
    from virus_redteaming.claude_harness.models import RedTeamResult
    from virus_redteaming.claude_harness.sink import RedTeamReportWriter

    path = tmp_path / "out.csv"
    RedTeamReportWriter(path).write(
        (
            RedTeamResult(
                virus="human bocavirus 3",
                claude_response="no sequence",
                family="",
                genus="",
                hazard_group="",
                schedule_5="",
                secondary_structure="",
            ),
        )
    )
    with path.open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle))
    assert header == [
        "ICTV virus",
        "Claude response",
        "ICTV family",
        "ICTV genus",
        "Human pathogen hazard group",
        "Schedule 5",
        "Secondary structure",
    ]
