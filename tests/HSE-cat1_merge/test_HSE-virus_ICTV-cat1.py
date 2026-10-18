"""Assess the HSE catalogue, the Category 1 table, and their merged file.

Levels:
1. The three CSVs exist and carry the columns the merge requires.
2. Category 1 rows are hazard group 1 and match the VMR exemplar.
3. NEN rows match the HSE catalogue and the VMR accession rule.
4. The merged file has the accepted shape: HSE rows, then Category 1 rows.
5. Every merged field follows the accepted column mapping.
6. The file on disk matches a fresh run of the merger.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from virus_redteaming.hse_cat1_merge.io import (
    Cat1CsvReader,
    HseCsvReader,
    MergedCsvWriter,
    VmrTaxonReader,
)
from virus_redteaming.hse_cat1_merge.models import MERGED_FIELDS, MergedVirusRow
from virus_redteaming.hse_cat1_merge.order import MergedTableOrder
from virus_redteaming.hse_cat1_merge.workflow import MergeHseAndCat1
from virus_redteaming.nen_accession.models import cleaned_virus_name
from virus_redteaming.nen_accession.parse import GenBankAccessionParser

_REPO = Path(__file__).resolve().parents[2]
_NEN = _REPO / "output" / "nen_viruses.csv"
_CAT1 = _REPO / "output" / "ICTV_cat1.csv"
_MERGED = _REPO / "output" / "HSE-virus_Cat1-virus_merged.csv"
_CATALOGUE = _REPO / "output" / "viruses.csv"
_VMR = _REPO / "docs" / "VMR_MSL41.v1.20260729.csv"

_NEN_FIELDS = (
    "Family",
    "Genus",
    "NEN genus",
    "Viruses",
    "NEN virus",
    "NCBI accession",
    "Human pathogen hazard group",
    "Schedule 5",
    "Issues",
)
_CAT1_FIELDS = (
    "Species",
    "Exemplar virus",
    "Family",
    "Genus",
    "Kingdom",
    "GenBank accessions",
    "RefSeq accessions",
    "Human pathogen hazard group",
    "Schedule 5",
    "Issues",
)
_CATALOGUE_FIELDS = (
    "Family",
    "Genus",
    "Virus",
    "Human pathogen hazard group",
    "Schedule 5",
)
_HAZARD = "Human pathogen hazard group"
_NEN_HAZARDS = frozenset({"2", "3", "3*", "4"})
_NEN_ISSUES = frozenset({"", "catchall", "unresolved name", "genus not in ICTV"})
_NEN_ROWS = 256
_CAT1_ROWS = 168
_CATALOGUE_ROWS = 232


@dataclass(frozen=True)
class _ChosenIsolate:
    is_exemplar: bool
    family: str
    species: str
    kingdom: str
    genbank: str
    raw_name: str


@dataclass(frozen=True)
class _Tables:
    nen: tuple[dict[str, str], ...]
    cat1: tuple[dict[str, str], ...]
    merged: tuple[dict[str, str], ...]
    catalogue: tuple[dict[str, str], ...]
    merged_fields: tuple[str, ...]
    vmr: dict[str, _ChosenIsolate]
    vmr_names: frozenset[str]


def _read(path: Path) -> tuple[tuple[str, ...], tuple[dict[str, str], ...]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = tuple(reader.fieldnames or ())
        rows = tuple({key: value or "" for key, value in row.items()} for row in reader)
    return fields, rows


def _choose_vmr(path: Path) -> tuple[dict[str, _ChosenIsolate], frozenset[str]]:
    chosen: dict[str, _ChosenIsolate] = {}
    names: set[str] = set()
    with path.open(encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle):
            raw_name = record["Virus name(s)"]
            names.add(raw_name)
            key = cleaned_virus_name(raw_name)
            if not key:
                continue
            is_exemplar = record["Exemplar or additional isolate"].strip() == "E"
            current = chosen.get(key)
            if current is not None and not (is_exemplar and not current.is_exemplar):
                continue
            chosen[key] = _ChosenIsolate(
                is_exemplar=is_exemplar,
                family=record["Family"],
                species=record["Species"],
                kingdom=record["Kingdom"],
                genbank=record["Virus GENBANK accession"],
                raw_name=raw_name,
            )
    return chosen, frozenset(names)


def _require(problems: list[str]) -> None:
    assert not problems, "\n".join(problems)


def _lookup(name: str, vmr: Mapping[str, _ChosenIsolate]) -> _ChosenIsolate | None:
    key = cleaned_virus_name(name)
    if not key:
        return None
    return vmr.get(key)


@pytest.fixture(scope="module")
def tables() -> _Tables:
    nen_fields, nen = _read(_NEN)
    cat1_fields, cat1 = _read(_CAT1)
    merged_fields, merged = _read(_MERGED)
    catalogue_fields, catalogue = _read(_CATALOGUE)
    assert nen_fields == _NEN_FIELDS
    assert cat1_fields == _CAT1_FIELDS
    assert catalogue_fields == _CATALOGUE_FIELDS
    vmr, vmr_names = _choose_vmr(_VMR)
    return _Tables(
        nen=nen,
        cat1=cat1,
        merged=merged,
        catalogue=catalogue,
        merged_fields=merged_fields,
        vmr=vmr,
        vmr_names=vmr_names,
    )


def _hse_expected(
    row: Mapping[str, str],
    vmr: Mapping[str, _ChosenIsolate],
) -> dict[str, str]:
    taxon = _lookup(row["NEN virus"], vmr)
    return {
        "Source": "HSE",
        "Catalogue family": row["Family"],
        "Catalogue genus": row["Genus"],
        "Catalogue virus": row["Viruses"],
        "ICTV family": taxon.family if taxon else "",
        "ICTV genus": row["NEN genus"],
        "ICTV virus": row["NEN virus"],
        "Species": taxon.species if taxon else "",
        "Kingdom": taxon.kingdom if taxon else "",
        "GenBank accessions": taxon.genbank if taxon else "",
        "NCBI accession": row["NCBI accession"],
        "RefSeq accessions": "",
        "Human pathogen hazard group": row[_HAZARD],
        "Schedule 5": row["Schedule 5"],
        "Issues": row["Issues"],
    }


def _cat1_expected(
    row: Mapping[str, str],
    parser: GenBankAccessionParser,
) -> dict[str, str]:
    return {
        "Source": "Cat1",
        "Catalogue family": "",
        "Catalogue genus": "",
        "Catalogue virus": "",
        "ICTV family": row["Family"],
        "ICTV genus": row["Genus"],
        "ICTV virus": row["Exemplar virus"],
        "Species": row["Species"],
        "Kingdom": row["Kingdom"],
        "GenBank accessions": row["GenBank accessions"],
        "NCBI accession": parser.join(row["GenBank accessions"]),
        "RefSeq accessions": row["RefSeq accessions"],
        "Human pathogen hazard group": row[_HAZARD],
        "Schedule 5": row["Schedule 5"],
        "Issues": row["Issues"],
    }


def _field_diffs(
    index: int,
    expected: Mapping[str, str],
    actual: Mapping[str, str],
) -> list[str]:
    diffs: list[str] = []
    for field in MERGED_FIELDS:
        if actual.get(field, "") != expected[field]:
            diffs.append(
                f"row {index} {field}: expected {expected[field]!r}, "
                f"got {actual.get(field, '')!r}"
            )
    return diffs


def test_level1_source_files_exist() -> None:
    missing = [
        str(path)
        for path in (_NEN, _CAT1, _MERGED, _CATALOGUE, _VMR)
        if not path.is_file()
    ]
    _require(missing)


def test_level1_headers_and_row_counts(tables: _Tables) -> None:
    problems: list[str] = []
    if tables.merged_fields != MERGED_FIELDS:
        problems.append(f"merged header {tables.merged_fields!r}")
    if len(tables.nen) != _NEN_ROWS:
        problems.append(f"nen rows {len(tables.nen)}")
    if len(tables.cat1) != _CAT1_ROWS:
        problems.append(f"cat1 rows {len(tables.cat1)}")
    if len(tables.catalogue) != _CATALOGUE_ROWS:
        problems.append(f"catalogue rows {len(tables.catalogue)}")
    if len(tables.merged) != _NEN_ROWS + _CAT1_ROWS:
        problems.append(f"merged rows {len(tables.merged)}")
    _require(problems)


def test_level2_cat1_is_hazard_group_1(tables: _Tables) -> None:
    problems: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(tables.cat1, start=2):
        exemplar = row["Exemplar virus"]
        if not exemplar:
            problems.append(f"line {index} blank exemplar")
        if exemplar in seen:
            problems.append(f"line {index} duplicate exemplar {exemplar!r}")
        seen.add(exemplar)
        if not row["GenBank accessions"]:
            problems.append(f"line {index} blank GenBank for {exemplar!r}")
        if row[_HAZARD] != "1":
            problems.append(f"line {index} hazard {row[_HAZARD]!r}")
        if row["Schedule 5"] != "0":
            problems.append(f"line {index} schedule {row['Schedule 5']!r}")
        if row["Issues"] != "":
            problems.append(f"line {index} issues {row['Issues']!r}")
    _require(problems)


def test_level2_cat1_exemplars_match_vmr(tables: _Tables) -> None:
    problems: list[str] = []
    for index, row in enumerate(tables.cat1, start=2):
        exemplar = row["Exemplar virus"]
        if exemplar not in tables.vmr_names:
            problems.append(f"line {index} {exemplar!r} is not a Virus name(s) cell")
            continue
        isolate = _lookup(exemplar, tables.vmr)
        if isolate is None:
            problems.append(f"line {index} {exemplar!r} has no chosen VMR isolate")
            continue
        if row["GenBank accessions"] != isolate.genbank:
            problems.append(
                f"line {index} {exemplar!r} GenBank {row['GenBank accessions']!r} "
                f"!= VMR {isolate.genbank!r}"
            )
        if row["Family"] != isolate.family:
            problems.append(
                f"line {index} {exemplar!r} family {row['Family']!r} "
                f"!= VMR {isolate.family!r}"
            )
        if row["Species"] != isolate.species:
            problems.append(
                f"line {index} {exemplar!r} species {row['Species']!r} "
                f"!= VMR {isolate.species!r}"
            )
        if row["Kingdom"] != isolate.kingdom:
            problems.append(
                f"line {index} {exemplar!r} kingdom {row['Kingdom']!r} "
                f"!= VMR {isolate.kingdom!r}"
            )
    _require(problems)


def test_level2_cat1_names_are_absent_from_nen(tables: _Tables) -> None:
    nen_names = {
        cleaned_virus_name(row["NEN virus"])
        for row in tables.nen
        if cleaned_virus_name(row["NEN virus"])
    }
    problems = [
        f"line {index} exemplar {row['Exemplar virus']!r} is also an NEN virus"
        for index, row in enumerate(tables.cat1, start=2)
        if cleaned_virus_name(row["Exemplar virus"]) in nen_names
    ]
    _require(problems)


def test_level3_nen_matches_hse_catalogue(tables: _Tables) -> None:
    by_virus = {row["Virus"]: row for row in tables.catalogue}
    problems: list[str] = []
    if len(by_virus) != len(tables.catalogue):
        problems.append("catalogue Virus values are not unique")
    for index, row in enumerate(tables.nen, start=2):
        catalogue = by_virus.get(row["Viruses"])
        if catalogue is None:
            problems.append(
                f"line {index} Viruses {row['Viruses']!r} is not in viruses.csv"
            )
            continue
        for field in ("Family", "Genus", _HAZARD, "Schedule 5"):
            source_field = "Virus" if field == "Viruses" else field
            if row[field] != catalogue[source_field]:
                problems.append(
                    f"line {index} {field} {row[field]!r} "
                    f"!= catalogue {catalogue[source_field]!r}"
                )
        if row[_HAZARD] not in _NEN_HAZARDS:
            problems.append(f"line {index} hazard {row[_HAZARD]!r}")
        if row["Schedule 5"] not in {"0", "1"}:
            problems.append(f"line {index} schedule {row['Schedule 5']!r}")
        if row["Issues"] not in _NEN_ISSUES:
            problems.append(f"line {index} issues {row['Issues']!r}")
    _require(problems)


def test_level3_nen_ncbi_follows_vmr_exemplar(tables: _Tables) -> None:
    parser = GenBankAccessionParser()
    problems: list[str] = []
    for index, row in enumerate(tables.nen, start=2):
        name = row["NEN virus"]
        isolate = _lookup(name, tables.vmr)
        if isolate is None:
            if row["NCBI accession"]:
                problems.append(
                    f"line {index} {name!r} has NCBI {row['NCBI accession']!r} "
                    "without a VMR name"
                )
            continue
        expected = parser.join(isolate.genbank)
        if row["NCBI accession"] != expected:
            problems.append(
                f"line {index} {name!r} NCBI {row['NCBI accession']!r} "
                f"!= parsed VMR {expected!r}"
            )
    _require(problems)


def test_level4_file_follows_the_sort_command(tables: _Tables) -> None:
    order = MergedTableOrder()
    keys = [
        order.sort_key(_merged_row(row), index)
        for index, row in enumerate(tables.merged)
    ]
    problems: list[str] = []
    if keys != sorted(keys):
        problems.append(
            "merged file is not ordered by ICTV genus, hazard group, then Schedule 5"
        )
    hse = sum(row["Source"] == "HSE" for row in tables.merged)
    cat1 = sum(row["Source"] == "Cat1" for row in tables.merged)
    if hse != _NEN_ROWS or cat1 != _CAT1_ROWS:
        problems.append(f"sources HSE {hse}, Cat1 {cat1}")
    _require(problems)


def test_level5_sorted_file_keeps_every_mapped_source_row(tables: _Tables) -> None:
    parser = GenBankAccessionParser()
    expected = [_hse_expected(row, tables.vmr) for row in tables.nen]
    expected.extend(_cat1_expected(row, parser) for row in tables.cat1)
    ordered = MergedTableOrder().sort(tuple(_merged_row(row) for row in expected))
    problems: list[str] = []
    if len(ordered) != len(tables.merged):
        problems.append(
            f"sorted merge has {len(ordered)} rows; disk has {len(tables.merged)}"
        )
    for index, row in enumerate(ordered):
        actual = tables.merged[index] if index < len(tables.merged) else {}
        mapped = dict(zip(MERGED_FIELDS, row.as_tuple(), strict=True))
        problems.extend(_field_diffs(index, mapped, actual))
    _require(problems)


def _merged_row(record: Mapping[str, str]) -> MergedVirusRow:
    return MergedVirusRow(
        source=record["Source"],
        catalogue_family=record["Catalogue family"],
        catalogue_genus=record["Catalogue genus"],
        catalogue_virus=record["Catalogue virus"],
        ictv_family=record["ICTV family"],
        ictv_genus=record["ICTV genus"],
        ictv_virus=record["ICTV virus"],
        species=record["Species"],
        kingdom=record["Kingdom"],
        genbank_accessions=record["GenBank accessions"],
        ncbi_accession=record["NCBI accession"],
        refseq_accessions=record["RefSeq accessions"],
        hazard_group=record["Human pathogen hazard group"],
        schedule_5=record["Schedule 5"],
        issues=record["Issues"],
    )


def test_level5_ictv_virus_sets_are_disjoint(tables: _Tables) -> None:
    hse = {
        cleaned_virus_name(row["ICTV virus"])
        for row in tables.merged
        if row["Source"] == "HSE" and cleaned_virus_name(row["ICTV virus"])
    }
    cat1 = {
        cleaned_virus_name(row["ICTV virus"])
        for row in tables.merged
        if row["Source"] == "Cat1" and cleaned_virus_name(row["ICTV virus"])
    }
    overlap = sorted(hse & cat1)
    _require([f"shared ICTV virus {name!r}" for name in overlap])


def test_level5_named_rows_keep_their_taxonomy(tables: _Tables) -> None:
    by_key = {
        (row["Source"], row["ICTV virus"] or row["Catalogue virus"]): row
        for row in tables.merged
    }
    dengue = by_key[("HSE", "dengue virus type 2")]
    rota = by_key[("HSE", "rotavirus A")]
    boca = by_key[("HSE", "human bocavirus 3")]
    adeno = next(
        row
        for row in tables.merged
        if row["Issues"] == "genus not in ICTV"
        and row["Catalogue virus"].startswith("Adenoviridae")
    )
    cat_rota = next(row for row in tables.merged if row["ICTV virus"] == "rotavirus H")
    problems: list[str] = []
    expected: Sequence[tuple[Mapping[str, str], str, str]] = (
        (dengue, "Catalogue virus", "Dengue virus"),
        (dengue, "ICTV family", "Flaviviridae"),
        (dengue, "Species", "Orthoflavivirus denguei"),
        (dengue, "GenBank accessions", "U87411"),
        (dengue, "NCBI accession", "U87411"),
        (dengue, _HAZARD, "3"),
        (dengue, "Schedule 5", "1"),
        (rota, "Catalogue family", "Reoviridae"),
        (rota, "ICTV family", "Sedoreoviridae"),
        (boca, "ICTV genus", "Bocaparvovirus"),
        (boca, "ICTV family", ""),
        (boca, "GenBank accessions", ""),
        (boca, "NCBI accession", ""),
        (adeno, "ICTV virus", ""),
        (adeno, "ICTV family", ""),
        (cat_rota, "Source", "Cat1"),
        (cat_rota, "ICTV family", "Sedoreoviridae"),
        (cat_rota, "Catalogue family", ""),
        (cat_rota, _HAZARD, "1"),
    )
    for row, field, value in expected:
        if row[field] != value:
            label = row["ICTV virus"] or row["Catalogue virus"]
            problems.append(f"{label} {field} is {row[field]!r}")
    _require(problems)


def test_level6_disk_file_matches_a_fresh_merge(tmp_path: Path) -> None:
    out = tmp_path / "merged.csv"
    MergeHseAndCat1(
        hse_reader=HseCsvReader(),
        cat1_reader=Cat1CsvReader(),
        vmr_reader=VmrTaxonReader(),
        writer=MergedCsvWriter(),
        parser=GenBankAccessionParser(),
        order=MergedTableOrder(),
    ).run(_NEN, _CAT1, _VMR, out)
    _, written = _read(out)
    _, on_disk = _read(_MERGED)
    problems = [
        f"row {index} differs from a fresh merge"
        for index, (left, right) in enumerate(zip(written, on_disk, strict=False))
        if left != right
    ]
    if len(written) != len(on_disk):
        problems.append(f"fresh merge has {len(written)} rows; disk has {len(on_disk)}")
    _require(problems)
