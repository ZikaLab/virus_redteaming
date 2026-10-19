"""The FASTA header is dropped into a sibling ``.tmp`` file."""

from pathlib import Path

from virus_redteaming.claude_harness.sequence import FastaSequence


def test_tmp_file_is_written_and_the_fasta_is_unchanged(tmp_path: Path) -> None:
    fasta = tmp_path / "V00603.fasta"
    original = ">V00603.1 label\nACGT ACGT\nTTTT\n"
    fasta.write_text(original, encoding="utf-8")
    prepared = FastaSequence(tmp_path).prepare("V00603")
    assert prepared == tmp_path / "V00603.tmp"
    assert prepared is not None
    assert prepared.read_text(encoding="utf-8") == "ACGT ACGT\nTTTT\n"
    assert fasta.read_text(encoding="utf-8") == original


def test_missing_fasta_prepares_nothing(tmp_path: Path) -> None:
    assert FastaSequence(tmp_path).prepare("V00603") is None
