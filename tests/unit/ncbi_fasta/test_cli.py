"""The command checks email, prints summary counts, and exits with the spec code."""

from pathlib import Path

import pytest

from virus_redteaming.__main__ import main
from virus_redteaming.clinical_fasta.errors import (
    FastaWriteError,
    NcbiFetchError,
    NcbiRecordRejected,
)
from virus_redteaming.core.errors import VirusRedteamingError
from virus_redteaming.ncbi_fasta.config import TOOL, entrez_config_from_environment
from virus_redteaming.ncbi_fasta.models import FetchNcbiFastaReport


def test_missing_email_exits_2(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("NCBI_EMAIL", raising=False)
    table = tmp_path / "merged.csv"
    table.write_text("GenBank accessions\nU87411\n", encoding="utf-8")
    code = main(
        [
            "fetch-ncbi-fasta",
            "--csv",
            str(table),
            "--out",
            str(tmp_path / "fasta"),
        ]
    )
    assert code == 2


def test_whitespace_email_exits_2(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("NCBI_EMAIL", "person @example.com")
    table = tmp_path / "merged.csv"
    table.write_text("GenBank accessions\nU87411\n", encoding="utf-8")
    code = main(
        [
            "fetch-ncbi-fasta",
            "--csv",
            str(table),
            "--out",
            str(tmp_path / "fasta"),
        ]
    )
    assert code == 2


def test_bad_table_exits_1(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("NCBI_EMAIL", "person@example.com")
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    table = tmp_path / "merged.csv"
    table.write_text("Virus\nflu\n", encoding="utf-8")
    code = main(
        [
            "fetch-ncbi-fasta",
            "--csv",
            str(table),
            "--out",
            str(tmp_path / "fasta"),
        ]
    )
    assert code == 1


@pytest.mark.parametrize(
    "error",
    [
        NcbiFetchError("efetch failed"),
        NcbiRecordRejected("header mismatch"),
        FastaWriteError("replace failed"),
    ],
)
def test_fetch_and_write_errors_exit_1(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    error: VirusRedteamingError,
) -> None:
    def _boom(csv_path: Path, out_dir: Path) -> FetchNcbiFastaReport:
        raise error

    monkeypatch.setattr("virus_redteaming.__main__._fetch_ncbi_fasta", _boom)
    code = main(
        [
            "fetch-ncbi-fasta",
            "--csv",
            str(tmp_path / "merged.csv"),
            "--out",
            str(tmp_path / "fasta"),
        ]
    )
    assert code == 1


def test_all_blank_table_exits_0(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("NCBI_EMAIL", "person@example.com")
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    table = tmp_path / "merged.csv"
    table.write_text(
        "Virus,GenBank accessions\nrow1,\nrow2,   \n",
        encoding="utf-8",
    )
    code = main(
        [
            "fetch-ncbi-fasta",
            "--csv",
            str(table),
            "--out",
            str(tmp_path / "fasta"),
        ]
    )
    assert code == 0
    assert capsys.readouterr().out.strip().splitlines() == [
        "skipped 2 blank rows",
        "cached 0 accessions",
        "fetched 0 accessions",
    ]


def test_cached_and_blank_table_exits_0_and_prints_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("NCBI_EMAIL", "person@example.com")
    monkeypatch.setenv("NCBI_API_KEY", "secret-key")
    out = tmp_path / "fasta"
    out.mkdir()
    (out / "V00603.fasta").write_text(">V00603.1\nACGT\n", encoding="utf-8")
    table = tmp_path / "merged.csv"
    table.write_text(
        "Virus,GenBank accessions\nrow1,\nrow2,V00603\n",
        encoding="utf-8",
    )
    code = main(
        [
            "fetch-ncbi-fasta",
            "--csv",
            str(table),
            "--out",
            str(out),
        ]
    )
    assert code == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines == [
        "skipped 1 blank rows",
        "cached 1 accessions",
        "fetched 0 accessions",
    ]


def test_written_paths_print_before_the_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    written = tmp_path / "V00603.fasta"
    cached = tmp_path / "J02151.fasta"
    report = FetchNcbiFastaReport((written,), (cached,), 1)

    def _report(csv_path: Path, out_dir: Path) -> FetchNcbiFastaReport:
        return report

    monkeypatch.setattr("virus_redteaming.__main__._fetch_ncbi_fasta", _report)
    code = main(
        [
            "fetch-ncbi-fasta",
            "--csv",
            str(tmp_path / "merged.csv"),
            "--out",
            str(tmp_path / "fasta"),
        ]
    )
    assert code == 0
    assert capsys.readouterr().out.strip().splitlines() == [
        str(written),
        "skipped 1 blank rows",
        "cached 1 accessions",
        "fetched 1 accessions",
    ]


def test_entrez_config_sets_ncbi_fasta_tool_and_optional_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NCBI_EMAIL", "person@example.com")
    monkeypatch.setenv("NCBI_API_KEY", "secret-key")
    config = entrez_config_from_environment()
    assert config.email == "person@example.com"
    assert config.tool == TOOL
    assert config.api_key == "secret-key"
    assert "secret-key" not in repr(config)


def test_empty_api_key_is_omitted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NCBI_EMAIL", "person@example.com")
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    assert entrez_config_from_environment().api_key is None
    monkeypatch.setenv("NCBI_API_KEY", "")
    assert entrez_config_from_environment().api_key is None
