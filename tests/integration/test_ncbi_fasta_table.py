"""The merged table's GenBank cells match the segment parser and the NCBI column."""

import csv
from pathlib import Path

from virus_redteaming.ncbi_fasta.parse import GenBankSegmentParser
from virus_redteaming.ncbi_fasta.source import MergedGenBankSource
from virus_redteaming.nen_accession.parse import GenBankAccessionParser

_REPO = Path(__file__).resolve().parents[2]
_MERGED = _REPO / "output" / "HSE-virus_Cat1-virus_merged.csv"


def test_merged_table_codes_match_the_established_parser() -> None:
    segment = GenBankSegmentParser()
    established = GenBankAccessionParser()
    influenza = "RNA1: V00603; RNA2: J02151"
    saw_influenza = False
    with _MERGED.open(encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle):
            cell = record["GenBank accessions"]
            codes = segment.codes(cell)
            assert codes == established.codes(cell)
            assert established.join(cell) == record["NCBI accession"]
            if cell.startswith(influenza):
                assert codes[:2] == ("V00603", "J02151")
                saw_influenza = True
    assert saw_influenza
    scan = MergedGenBankSource(_MERGED, segment).read()
    assert scan.blank_rows == 33
    assert len(scan.codes) == 727
    assert Path(_MERGED).is_file()
