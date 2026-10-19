"""DirectoryFastaCache checks single-record UTF-8 FASTA files."""

from pathlib import Path

from virus_redteaming.clinical_fasta.fasta_source import AccessionIdentity
from virus_redteaming.ncbi_fasta.cache import DirectoryFastaCache


def _cache(directory: Path) -> DirectoryFastaCache:
    return DirectoryFastaCache(directory, AccessionIdentity())


def test_missing_file_returns_none(tmp_path: Path) -> None:
    assert _cache(tmp_path).cached("V00603") is None


def test_valid_single_record_is_a_hit(tmp_path: Path) -> None:
    path = tmp_path / "V00603.fasta"
    path.write_text(">V00603.1 influenza\nACGT\n", encoding="utf-8")
    assert _cache(tmp_path).cached("V00603") == path


def test_empty_or_non_fasta_file_returns_none(tmp_path: Path) -> None:
    (tmp_path / "V00603.fasta").write_text("", encoding="utf-8")
    (tmp_path / "J02151.fasta").write_text("plain text\n", encoding="utf-8")
    cache = _cache(tmp_path)
    assert cache.cached("V00603") is None
    assert cache.cached("J02151") is None


def test_multiple_records_return_none(tmp_path: Path) -> None:
    (tmp_path / "V00603.fasta").write_text(
        ">V00603.1 first\nACGT\n>V00603.1 second\nTGCA\n",
        encoding="utf-8",
    )
    assert _cache(tmp_path).cached("V00603") is None


def test_unreadable_utf8_bytes_return_none(tmp_path: Path) -> None:
    (tmp_path / "V00603.fasta").write_bytes(b"\xff\xfe\x00\x00")
    assert _cache(tmp_path).cached("V00603") is None
