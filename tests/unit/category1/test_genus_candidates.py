"""Genus candidate lists stay inside the catalogue family, plus one stem case."""

from __future__ import annotations

from virus_redteaming.category1.candidates import GenusCandidateList
from virus_redteaming.category1.inventory import IctvGenusInventory
from virus_redteaming.category1.models import CatalogueVirus, IctvSpecies


def _species(index: int, family: str, genus: str, exemplar: str = "x") -> IctvSpecies:
    return IctvSpecies(
        source_index=index,
        species=f"s{index}",
        exemplar=exemplar,
        family=family,
        genus=genus,
        kingdom="k",
        genbank="",
        refseq="",
    )


def _row(family: str, genus: str, virus: str = "v") -> CatalogueVirus:
    return CatalogueVirus(0, family, genus, virus)


def test_family_scope_for_nairoviridae() -> None:
    inventory = IctvGenusInventory(
        (
            _species(0, "Nairoviridae", "Orthonairovirus"),
            _species(1, "Nairoviridae", "Othernairo"),
            _species(2, "Flaviviridae", "Orthoflavivirus"),
        )
    )
    found = GenusCandidateList().candidates(
        _row("Nairoviridae", "Ortonairovirus"),
        inventory,
    )
    assert found == ("Orthonairovirus", "Othernairo")
    assert "Orthonairovirus" in found


def test_hepacivirus_stem_adds_orthohepacivirus() -> None:
    inventory = IctvGenusInventory(
        (
            _species(0, "Flaviviridae", "Orthoflavivirus"),
            _species(1, "Hepaciviridae", "Orthohepacivirus"),
            _species(2, "Totiviridae", "Totivirus"),
        )
    )
    row = _row("Flaviviridae", "Hepacivirus")
    found = GenusCandidateList().candidates(row, inventory)
    assert "Orthohepacivirus" in found
    assert "Orthoflavivirus" in found
    assert "Totivirus" not in found
    assert set(found) != set(inventory.genera())


def test_genus_already_in_family_skips_the_stem() -> None:
    inventory = IctvGenusInventory(
        (
            _species(0, "Caliciviridae", "Norovirus"),
            _species(1, "Caliciviridae", "Sapovirus"),
            _species(2, "Elsewhere", "Norovirusextra"),
        )
    )
    row = _row("Caliciviridae", "Norovirus")
    found = GenusCandidateList().candidates(row, inventory)
    assert found == ("Norovirus", "Sapovirus")
    assert "Norovirusextra" not in found


def test_dna_family_has_no_candidates() -> None:
    inventory = IctvGenusInventory((_species(0, "Flaviviridae", "Orthoflavivirus"),))
    found = GenusCandidateList().candidates(
        _row("Adenoviridae", "Mastadenovirus"),
        inventory,
    )
    assert found == ()


def test_candidate_list_is_not_the_full_genus_inventory() -> None:
    inventory = IctvGenusInventory(
        (
            _species(0, "FamilyA", "GenusA"),
            _species(1, "FamilyB", "GenusB"),
        )
    )
    found = GenusCandidateList().candidates(_row("FamilyA", "GenusA"), inventory)
    assert found == ("GenusA",)
    assert "GenusB" not in found
