"""The FASTA header is copied into a separate sequence directory."""

from pathlib import Path

from virus_redteaming.claude_harness.sequence import FastaSequence


def test_tmp_file_is_written_and_the_fasta_is_unchanged(tmp_path: Path) -> None:
    source = tmp_path / "fasta"
    destination = tmp_path / "sequences"
    source.mkdir()
    fasta = source / "V00603.fasta"
    original = ">V00603.1 label\nACGT ACGT\nTTTT\n"
    fasta.write_text(original, encoding="utf-8")
    prepared = FastaSequence(source, destination).prepare("V00603")
    assert prepared == destination / "V00603.txt"
    assert prepared is not None
    assert prepared.read_text(encoding="utf-8") == "ACGT ACGT\nTTTT\n"
    assert fasta.read_text(encoding="utf-8") == original
    assert list(source.glob("*.txt")) == []


def test_missing_fasta_prepares_nothing(tmp_path: Path) -> None:
    source = tmp_path / "fasta"
    source.mkdir()
    assert FastaSequence(source, tmp_path / "sequences").prepare("V00603") is None
