"""The response CSV quotes a multiline structure and replaces the file last."""

import os
from pathlib import Path

import pytest

from virus_redteaming.claude_harness.models import RedTeamResult
from virus_redteaming.claude_harness.sink import RedTeamReportWriter
from virus_redteaming.core.errors import VirusRedteamingError


def _result(structure: str) -> RedTeamResult:
    return RedTeamResult(
        virus="flu",
        claude_response="2341",
        family="Fam",
        genus="Gen",
        hazard_group="3",
        schedule_5="0",
        secondary_structure=structure,
    )


def test_structure_newline_stays_inside_one_cell(tmp_path: Path) -> None:
    path = tmp_path / "out.csv"
    RedTeamReportWriter(path).write((_result("((((....))))\n...."),))
    text = path.read_text(encoding="utf-8")
    assert text.startswith(
        "ICTV virus,Claude response,ICTV family,ICTV genus,"
        "Human pathogen hazard group,Schedule 5,Secondary structure\n"
    )
    assert '"((((....))))\n...."' in text


def test_interrupted_write_leaves_the_previous_csv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "out.csv"
    path.write_text("previous\n", encoding="utf-8")

    def _fail(src: Path, dst: Path) -> None:
        raise OSError("disk")

    monkeypatch.setattr(os, "replace", _fail)
    with pytest.raises(VirusRedteamingError):
        RedTeamReportWriter(path).write((_result("."),))
    assert path.read_text(encoding="utf-8") == "previous\n"
