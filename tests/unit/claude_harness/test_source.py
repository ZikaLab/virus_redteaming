"""The merged table contributes one accession, the text before the first semicolon."""

from pathlib import Path

import pytest

from virus_redteaming.claude_harness.source import MergedRedTeamSource
from virus_redteaming.core.errors import VirusRedteamingError

_HEADER = (
    "ICTV virus,NCBI accession,ICTV family,ICTV genus,"
    "Human pathogen hazard group,Schedule 5\n"
)


def _table(path: Path, body: str) -> Path:
    path.write_text(_HEADER + body, encoding="utf-8")
    return path


def test_semicolon_stops_the_row_after_the_first_code(tmp_path: Path) -> None:
    path = _table(tmp_path / "t.csv", "flu,V00603; J02151,Fam,Gen,3,1\n")
    rows = MergedRedTeamSource(path).read()
    assert [row.accession for row in rows] == ["V00603"]


def test_blank_key_and_accession_are_skipped(tmp_path: Path) -> None:
    path = _table(tmp_path / "t.csv", ",,Fam,Gen,3,0\nflu,V00603,Fam,Gen,3,0\n")
    rows = MergedRedTeamSource(path).read()
    assert [row.virus for row in rows] == ["flu"]


def test_named_row_without_accession_is_kept(tmp_path: Path) -> None:
    path = _table(tmp_path / "t.csv", "human bocavirus 3,,Fam,Gen,2,0\n")
    rows = MergedRedTeamSource(path).read()
    assert len(rows) == 1
    assert rows[0].accession == ""
    assert rows[0].virus == "human bocavirus 3"


def test_missing_column_raises(tmp_path: Path) -> None:
    path = tmp_path / "t.csv"
    path.write_text("ICTV virus,NCBI accession\nflu,V00603\n", encoding="utf-8")
    with pytest.raises(VirusRedteamingError):
        MergedRedTeamSource(path).read()
