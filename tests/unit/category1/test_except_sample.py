"""EXCEPT removes named exemplars. The sample is the source-order prefix."""

from __future__ import annotations

from virus_redteaming.category1.except_sample import (
    GenusCategory1Sampler,
    GenusVirusExcept,
)
from virus_redteaming.category1.inventory import IctvGenusInventory
from virus_redteaming.category1.models import IctvSpecies, NenRow


def _species(index: int, genus: str, exemplar: str) -> IctvSpecies:
    return IctvSpecies(index, f"s{index}", exemplar, "Fam", genus, "k", "", "")


def _nen(
    index: int,
    nen_genus: str,
    nen_virus: str,
    genus: str = "CatGenus",
    viruses: str = "v",
) -> NenRow:
    return NenRow(index, "Fam", genus, nen_genus, viruses, nen_virus, "")


def test_except_removes_only_named_exemplars() -> None:
    inventory = IctvGenusInventory(
        (
            _species(0, "G", "keep-me"),
            _species(1, "G", "drop-me"),
            _species(2, "G", "later"),
        )
    )
    remainder = GenusVirusExcept().remainder(inventory, (_nen(0, "G", "drop-me"),))
    assert [row.exemplar for row in remainder["G"]] == ["keep-me", "later"]


def test_unknown_nen_virus_removes_nothing() -> None:
    inventory = IctvGenusInventory(
        (_species(0, "G", "real-a"), _species(1, "G", "real-b"))
    )
    remainder = GenusVirusExcept().remainder(
        inventory, (_nen(0, "G", "not-an-exemplar"),)
    )
    assert [row.exemplar for row in remainder["G"]] == ["real-a", "real-b"]


def test_semicolon_exemplar_is_removed_whole() -> None:
    mixed = "enterovirus E1; bovine enterovirus 1"
    inventory = IctvGenusInventory(
        (
            _species(0, "Enterovirus", mixed),
            _species(1, "Enterovirus", "next"),
        )
    )
    remainder = GenusVirusExcept().remainder(
        inventory, (_nen(0, "Enterovirus", mixed),)
    )
    assert [row.exemplar for row in remainder["Enterovirus"]] == ["next"]


def test_sample_is_the_first_n_in_source_order() -> None:
    species = tuple(_species(index, "G", f"e{index}") for index in range(4))
    inventory = IctvGenusInventory(species)
    nen = (_nen(0, "G", ""), _nen(1, "G", ""))
    remainder = GenusVirusExcept().remainder(inventory, nen)
    sample = GenusCategory1Sampler().sample(nen, remainder)
    assert len(remainder["G"]) == 4
    assert [row.source_index for row in sample] == [0, 1]


def test_short_remainder_is_not_padded() -> None:
    inventory = IctvGenusInventory((_species(0, "G", "only"),))
    nen = tuple(_nen(index, "G", "") for index in range(5))
    remainder = GenusVirusExcept().remainder(inventory, nen)
    sample = GenusCategory1Sampler().sample(nen, remainder)
    assert len(sample) == 1


def test_split_genus_counts_each_nen_genus() -> None:
    inventory = IctvGenusInventory(
        (
            _species(0, "Norovirus", "Norwalk virus"),
            _species(1, "Norovirus", "extra norovirus"),
            _species(2, "Sapovirus", "Sapporo virus"),
            _species(3, "Sapovirus", "extra sapporo"),
        )
    )
    nen = (
        _nen(0, "Norovirus", "", genus="Norovirus", viruses="Norwalk virus"),
        _nen(1, "Sapovirus", "", genus="Norovirus", viruses="Sapporo virus"),
    )
    remainder = GenusVirusExcept().remainder(inventory, nen)
    sample = GenusCategory1Sampler().sample(nen, remainder)
    norovirus = [row.exemplar for row in sample if row.genus == "Norovirus"]
    sapovirus = [row.exemplar for row in sample if row.genus == "Sapovirus"]
    assert norovirus == ["Norwalk virus"]
    assert sapovirus == ["Sapporo virus"]


def test_expanded_serotypes_count_as_one_catalogue_row() -> None:
    species = tuple(_species(index, "Deltavirus", f"hdv{index}") for index in range(3))
    inventory = IctvGenusInventory(species)
    nen = tuple(_nen(0, "Deltavirus", "") for _ in range(3))
    remainder = GenusVirusExcept().remainder(inventory, nen)
    sample = GenusCategory1Sampler().sample(nen, remainder)
    assert len(sample) == 1
    assert sample[0].exemplar == "hdv0"
