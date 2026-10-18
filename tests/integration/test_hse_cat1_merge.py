"""The merged table stacks the repository HSE and Category 1 files."""

import csv
from pathlib import Path

from virus_redteaming.hse_cat1_merge.io import (
    Cat1CsvReader,
    HseCsvReader,
    MergedCsvWriter,
    VmrTaxonReader,
)
from virus_redteaming.hse_cat1_merge.models import MERGED_FIELDS, MergedVirusRow
from virus_redteaming.hse_cat1_merge.order import MergedTableOrder
from virus_redteaming.hse_cat1_merge.workflow import MergeHseAndCat1
from virus_redteaming.nen_accession.parse import GenBankAccessionParser

_REPO = Path(__file__).resolve().parents[2]


def test_repository_merge_stacks_every_row(tmp_path: Path) -> None:
    out = tmp_path / "merged.csv"
    count = MergeHseAndCat1(
        hse_reader=HseCsvReader(),
        cat1_reader=Cat1CsvReader(),
        vmr_reader=VmrTaxonReader(),
        writer=MergedCsvWriter(),
        parser=GenBankAccessionParser(),
        order=MergedTableOrder(),
    ).run(
        _REPO / "output" / "nen_viruses.csv",
        _REPO / "output" / "ICTV_cat1.csv",
        _REPO / "docs" / "VMR_MSL41.v1.20260729.csv",
        out,
    )
    with out.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert count == 424
    assert len(rows) == 424
    assert list(rows[0]) == list(MERGED_FIELDS)
    assert [row["Source"] for row in rows].count("HSE") == 256
    assert [row["Source"] for row in rows].count("Cat1") == 168
    order = MergedTableOrder()
    keys = [order.sort_key(_merged_row(row), index) for index, row in enumerate(rows)]
    assert keys == sorted(keys)

    dengue = next(row for row in rows if row["ICTV virus"] == "dengue virus type 2")
    assert dengue["Source"] == "HSE"
    assert dengue["Catalogue virus"] == "Dengue virus"
    assert dengue["GenBank accessions"] == "U87411"
    assert dengue["NCBI accession"] == "U87411"
    assert dengue["Human pathogen hazard group"] == "3"
    assert dengue["Schedule 5"] == "1"
    assert dengue["ICTV family"] == "Flaviviridae"
    assert dengue["Species"] == "Orthoflavivirus denguei"

    hse_rota = next(
        row
        for row in rows
        if row["Source"] == "HSE" and row["ICTV virus"] == "rotavirus A"
    )
    cat_rota = next(
        row
        for row in rows
        if row["Source"] == "Cat1" and row["ICTV genus"] == "Rotavirus"
    )
    assert hse_rota["Catalogue family"] == "Reoviridae"
    assert cat_rota["Catalogue family"] == ""
    assert cat_rota["ICTV family"] == "Sedoreoviridae"
    assert cat_rota["Human pathogen hazard group"] == "1"

    bocavirus = next(row for row in rows if row["ICTV virus"] == "human bocavirus 3")
    assert bocavirus["ICTV genus"] == "Bocaparvovirus"
    assert bocavirus["ICTV family"] == ""
    assert bocavirus["GenBank accessions"] == ""

    blank = next(row for row in rows if row["Issues"] == "genus not in ICTV")
    assert blank["ICTV virus"] == ""
    assert blank["Catalogue virus"] != ""

    hse_names = {
        row["ICTV virus"]
        for row in rows
        if row["Source"] == "HSE" and row["ICTV virus"]
    }
    cat_names = {row["ICTV virus"] for row in rows if row["Source"] == "Cat1"}
    assert hse_names.isdisjoint(cat_names)


def _merged_row(record: dict[str, str]) -> MergedVirusRow:
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
