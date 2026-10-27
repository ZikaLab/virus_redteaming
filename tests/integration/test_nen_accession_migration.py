"""One hundred checks that each filled NCBI accession matches the VMR.

Each case reads one row of output/nen_viruses.csv, finds that NEN virus
in the VMR Virus name(s) column, and compares the NCBI accession cell
with the codes in Virus GENBANK accession. The first exemplar row is
the one that counts. When a name has no exemplar, the first VMR row is
used. Cases are the first 100 nen rows whose NCBI accession cell is
not empty, in file order.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from virus_redteaming.nen_accession.models import cleaned_virus_name
from virus_redteaming.nen_accession.parse import GenBankAccessionParser

_REPO = Path(__file__).resolve().parents[2]
_NEN = _REPO / "output" / "nen_viruses.csv"
_VMR = _REPO / "docs" / "VMR_MSL41.v1.20260729.csv"
_SAMPLE = 100
_PARSER = GenBankAccessionParser()


def _load_vmr() -> dict[str, tuple[str, ...]]:
    """Map a cleaned virus name to GenBank cells, exemplar first."""
    grouped: dict[str, list[tuple[bool, str]]] = {}
    with _VMR.open(encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle):
            name = cleaned_virus_name(record["Virus name(s)"])
            if not name:
                continue
            is_exemplar = record["Exemplar or additional isolate"].strip() == "E"
            grouped.setdefault(name, []).append(
                (is_exemplar, record["Virus GENBANK accession"])
            )
    chosen: dict[str, tuple[str, ...]] = {}
    for name, rows in grouped.items():
        exemplars = [field for is_exemplar, field in rows if is_exemplar]
        fields = exemplars or [field for _flag, field in rows]
        chosen[name] = tuple(fields)
    return chosen


def _sample_rows() -> list[tuple[int, str, str]]:
    selected: list[tuple[int, str, str]] = []
    with _NEN.open(encoding="utf-8", newline="") as handle:
        for row_number, record in enumerate(csv.DictReader(handle), start=2):
            accession = record["NCBI accession"].strip()
            if not accession:
                continue
            selected.append((row_number, record["NEN virus"], record["NCBI accession"]))
            if len(selected) == _SAMPLE:
                break
    if len(selected) != _SAMPLE:
        message = f"nen file has {len(selected)} filled NCBI rows, need {_SAMPLE}"
        raise RuntimeError(message)
    return selected


_VMR_BY_NAME = _load_vmr()
_CASES = _sample_rows()


def _case_id(case: tuple[int, str, str]) -> str:
    row_number, nen_virus, _accession = case
    safe = nen_virus.replace(" ", "_")
    return f"row{row_number}-{safe}"


_IDS = [_case_id(case) for case in _CASES]


@pytest.mark.parametrize(
    ("row_number", "nen_virus", "ncbi_accession"),
    _CASES,
    ids=_IDS,
)
def test_nen_virus_accession_matches_vmr_genbank(
    row_number: int,
    nen_virus: str,
    ncbi_accession: str,
) -> None:
    name = cleaned_virus_name(nen_virus)
    fields = _VMR_BY_NAME.get(name)
    assert fields, f"row {row_number}: {nen_virus!r} is not a VMR Virus name(s) value"
    genbank_field = fields[0]
    codes = _PARSER.join(genbank_field)
    assert ncbi_accession == codes, (
        f"row {row_number}: {nen_virus!r} NCBI accession {ncbi_accession!r} "
        f"does not match Virus GENBANK accession {genbank_field!r} ({codes!r})"
    )


def test_migration_sample_covers_one_hundred_filled_rows() -> None:
    assert len(_CASES) == _SAMPLE
    assert len({case[0] for case in _CASES}) == _SAMPLE
