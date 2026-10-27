"""Tiny CSVs through BuildCategory1. Sources stay unchanged."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from virus_redteaming.category1.candidates import GenusCandidateList
from virus_redteaming.category1.except_sample import (
    GenusCategory1Sampler,
    GenusVirusExcept,
)
from virus_redteaming.category1.harmonize import NenHarmonizer
from virus_redteaming.category1.inventory import CatalogueGenusIndex
from virus_redteaming.category1.models import CatalogueVirus, NenRow
from virus_redteaming.category1.workflow import BuildCategory1, Category1PromptRequired
from virus_redteaming.category1.write import IctvCat1Writer, NenReader, NenWriter

ICTV_HEADER = (
    "Species",
    "Exemplar virus",
    "Family",
    "Genus",
    "Kingdom",
    "GenBank accessions",
    "RefSeq accessions",
)


def _write_ictv(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(ICTV_HEADER)
        writer.writerow(("Alpha one", "virus-a", "Fam", "GenusA", "King", "ga", "ra"))
        writer.writerow(("Alpha two", "virus-b", "Fam", "GenusA", "King", "gb", "rb"))


def _write_catalogue(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("Family", "Genus", "Virus"))
        writer.writerow(("Fam", "GenusA", "virus-a"))


class _Genus:
    def __init__(self) -> None:
        self.calls = 0

    def choose(self, row: CatalogueVirus, candidates: tuple[str, ...]) -> str | None:
        self.calls += 1
        return None


class _Virus:
    def __init__(self) -> None:
        self.calls = 0

    def choose(
        self,
        nen_genus: str,
        virus: str,
        exemplars: tuple[str, ...],
    ) -> tuple[str, ...]:
        self.calls += 1
        if virus in exemplars:
            return (virus,)
        return ()


class _BoomGenus:
    def choose(self, row: CatalogueVirus, candidates: tuple[str, ...]) -> str | None:
        raise AssertionError("genus prompt called")


class _BoomVirus:
    def choose(
        self,
        nen_genus: str,
        virus: str,
        exemplars: tuple[str, ...],
    ) -> tuple[str, ...]:
        raise AssertionError("virus prompt called")


def _workflow(genus: _Genus | _BoomGenus, virus: _Virus | _BoomVirus) -> BuildCategory1:
    return BuildCategory1(
        catalogue_index=CatalogueGenusIndex(),
        harmonizer=NenHarmonizer(GenusCandidateList(), genus, virus),
        exceptor=GenusVirusExcept(),
        sampler=GenusCategory1Sampler(),
        nen_writer=NenWriter(),
        nen_reader=NenReader(),
        cat1_writer=IctvCat1Writer(),
    )


def _bare_workflow() -> BuildCategory1:
    return BuildCategory1(
        catalogue_index=CatalogueGenusIndex(),
        harmonizer=None,
        exceptor=GenusVirusExcept(),
        sampler=GenusCategory1Sampler(),
        nen_writer=NenWriter(),
        nen_reader=NenReader(),
        cat1_writer=IctvCat1Writer(),
    )


def test_workflow_writes_both_outputs(tmp_path: Path) -> None:
    viruses = tmp_path / "viruses.csv"
    ictv = tmp_path / "ictv.csv"
    nen = tmp_path / "nen.csv"
    out = tmp_path / "cat1.csv"
    _write_catalogue(viruses)
    _write_ictv(ictv)
    _workflow(_Genus(), _Virus()).run(viruses, ictv, nen, out, refresh=True)
    assert nen.exists()
    assert out.exists()
    with out.open(encoding="utf-8", newline="") as handle:
        exemplars = [row["Exemplar virus"] for row in csv.DictReader(handle)]
    assert "virus-a" not in exemplars
    assert exemplars == ["virus-b"]


def test_workflow_does_not_rewrite_sources(tmp_path: Path) -> None:
    viruses = tmp_path / "viruses.csv"
    ictv = tmp_path / "ictv.csv"
    _write_catalogue(viruses)
    _write_ictv(ictv)
    before = (viruses.read_bytes(), ictv.read_bytes())
    _workflow(_Genus(), _Virus()).run(
        viruses,
        ictv,
        tmp_path / "nen.csv",
        tmp_path / "cat1.csv",
        refresh=True,
    )
    assert (viruses.read_bytes(), ictv.read_bytes()) == before


def test_existing_nen_skips_prompts(tmp_path: Path) -> None:
    viruses = tmp_path / "viruses.csv"
    ictv = tmp_path / "ictv.csv"
    nen = tmp_path / "nen.csv"
    out = tmp_path / "cat1.csv"
    _write_catalogue(viruses)
    _write_ictv(ictv)
    NenWriter().write(
        nen,
        (NenRow(0, "Fam", "GenusA", "GenusA", "virus-a", "virus-a", ""),),
    )
    _workflow(_BoomGenus(), _BoomVirus()).run(viruses, ictv, nen, out, refresh=False)
    with out.open(encoding="utf-8", newline="") as handle:
        exemplars = [row["Exemplar virus"] for row in csv.DictReader(handle)]
    assert exemplars == ["virus-b"]


def test_missing_nen_without_harmonizer_raises(tmp_path: Path) -> None:
    viruses = tmp_path / "viruses.csv"
    ictv = tmp_path / "ictv.csv"
    nen = tmp_path / "missing.csv"
    out = tmp_path / "cat1.csv"
    _write_catalogue(viruses)
    _write_ictv(ictv)
    with pytest.raises(Category1PromptRequired):
        _bare_workflow().run(viruses, ictv, nen, out, refresh=False)
    assert not out.exists()
    assert not nen.exists()
