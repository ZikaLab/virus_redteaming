"""Prompt order for NEN genus and NEN virus."""

from __future__ import annotations

from virus_redteaming.category1.candidates import GenusCandidateList
from virus_redteaming.category1.harmonize import NenHarmonizer
from virus_redteaming.category1.inventory import IctvGenusInventory
from virus_redteaming.category1.models import CatalogueVirus, IctvSpecies


def _species(index: int, family: str, genus: str, exemplar: str) -> IctvSpecies:
    return IctvSpecies(index, f"s{index}", exemplar, family, genus, "k", "", "")


def _row(family: str, genus: str, virus: str, index: int = 0) -> CatalogueVirus:
    return CatalogueVirus(index, family, genus, virus)


class _Genus:
    def __init__(self, reply: str | None, calls: list[str] | None = None) -> None:
        self.reply = reply
        self.calls = calls if calls is not None else []

    def choose(self, row: CatalogueVirus, candidates: tuple[str, ...]) -> str | None:
        self.calls.append("genus")
        if self.reply is not None and self.reply in candidates:
            return self.reply
        return self.reply


class _Virus:
    def __init__(
        self,
        by_genus: dict[str, tuple[str, ...]],
        calls: list[str] | None = None,
    ) -> None:
        self.by_genus = by_genus
        self.calls: list[tuple[str, str]] = []
        self.order = calls if calls is not None else []

    def choose(
        self,
        nen_genus: str,
        virus: str,
        exemplars: tuple[str, ...],
    ) -> tuple[str, ...]:
        self.order.append("virus")
        self.calls.append((nen_genus, virus))
        offered = self.by_genus.get(nen_genus, ())
        return tuple(item for item in offered if item in exemplars)


def _harmonizer(
    genus: _Genus,
    virus: _Virus,
) -> NenHarmonizer:
    return NenHarmonizer(GenusCandidateList(), genus, virus)


def test_exact_genus_does_not_call_genus_prompt() -> None:
    inventory = IctvGenusInventory(
        (_species(0, "Caliciviridae", "Norovirus", "Norwalk virus"),)
    )
    genus = _Genus("should-not-run")
    virus = _Virus({"Norovirus": ("Norwalk virus",)})
    rows = _harmonizer(genus, virus).harmonize(
        (_row("Caliciviridae", "Norovirus", "Norwalk virus"),),
        inventory,
    )
    assert genus.calls == []
    assert virus.calls == [("Norovirus", "Norwalk virus")]
    assert rows[0].nen_genus == "Norovirus"
    assert rows[0].nen_virus == "Norwalk virus"


def test_sapporo_retries_genus_after_virus_miss() -> None:
    inventory = IctvGenusInventory(
        (
            _species(0, "Caliciviridae", "Norovirus", "Norwalk virus"),
            _species(1, "Caliciviridae", "Sapovirus", "Sapporo virus"),
        )
    )
    order: list[str] = []
    genus = _Genus("Sapovirus", order)
    virus = _Virus({"Norovirus": (), "Sapovirus": ("Sapporo virus",)}, order)
    rows = _harmonizer(genus, virus).harmonize(
        (_row("Caliciviridae", "Norovirus", "Sapporo virus"),),
        inventory,
    )
    assert order == ["virus", "genus", "virus"]
    assert virus.calls[0][0] == "Norovirus"
    assert virus.calls[1][0] == "Sapovirus"
    assert rows[0].nen_genus == "Sapovirus"
    assert rows[0].nen_virus == "Sapporo virus"


def test_ortonairovirus_prompts_genus_first() -> None:
    inventory = IctvGenusInventory(
        (_species(0, "Nairoviridae", "Orthonairovirus", "Hazara virus"),)
    )
    order: list[str] = []
    genus = _Genus("Orthonairovirus", order)
    virus = _Virus({"Orthonairovirus": ("Hazara virus",)}, order)
    rows = _harmonizer(genus, virus).harmonize(
        (_row("Nairoviridae", "Ortonairovirus", "Hazara virus"),),
        inventory,
    )
    assert order == ["genus", "virus"]
    assert rows[0].nen_genus == "Orthonairovirus"
    assert rows[0].nen_virus == "Hazara virus"


def test_blank_astroviridae_resolves_mamastrovirus() -> None:
    inventory = IctvGenusInventory(
        (
            _species(0, "Astroviridae", "Mamastrovirus", "mamastrovirus 1"),
            _species(1, "Astroviridae", "Mamastrovirus", "mamastrovirus 2"),
        )
    )
    genus = _Genus("Mamastrovirus")
    virus = _Virus({"Mamastrovirus": ("mamastrovirus 1",)})
    rows = _harmonizer(genus, virus).harmonize(
        (
            _row(
                "Astroviridae",
                "",
                "Astroviridae spp. known to be pathogenic in humans",
            ),
        ),
        inventory,
    )
    assert len(rows) == 1
    assert rows[0].nen_genus == "Mamastrovirus"
    assert rows[0].nen_virus == "mamastrovirus 1"
    assert rows[0].issues == ""


def test_non_rna_genus_is_empty() -> None:
    inventory = IctvGenusInventory(
        (_species(0, "Flaviviridae", "Orthoflavivirus", "Zika virus"),)
    )
    order: list[str] = []
    genus = _Genus(None, order)
    virus = _Virus({}, order)
    rows = _harmonizer(genus, virus).harmonize(
        (_row("Poxviridae", "Orthopoxvirus", "Variola virus"),),
        inventory,
    )
    assert order == ["genus"]
    assert rows[0].nen_genus == ""
    assert rows[0].nen_virus == ""
    assert rows[0].issues == "genus not in ICTV"


def test_off_list_genus_is_dropped() -> None:
    inventory = IctvGenusInventory(
        (_species(0, "Flaviviridae", "Orthoflavivirus", "Zika virus"),)
    )
    genus = _Genus("NotAGenus")
    virus = _Virus({})
    rows = _harmonizer(genus, virus).harmonize(
        (_row("Poxviridae", "Orthopoxvirus", "Variola virus"),),
        inventory,
    )
    assert virus.calls == []
    assert rows[0].nen_genus == ""
    assert rows[0].issues == "genus not in ICTV"


def test_exact_genus_kept_when_retry_finds_nothing() -> None:
    inventory = IctvGenusInventory(
        (
            _species(0, "Flaviviridae", "Orthoflavivirus", "Zika virus"),
            _species(1, "Flaviviridae", "Pegivirus", "human pegivirus"),
        )
    )
    genus = _Genus("Pegivirus")
    virus = _Virus({})
    rows = _harmonizer(genus, virus).harmonize(
        (_row("Flaviviridae", "Orthoflavivirus", "Sal Vieja virus"),),
        inventory,
    )
    assert [call[0] for call in virus.calls] == ["Orthoflavivirus", "Pegivirus"]
    assert rows[0].nen_genus == "Orthoflavivirus"
    assert rows[0].nen_virus == ""
    assert rows[0].issues == "unresolved name"


def test_catchall_spp_does_not_move_genus() -> None:
    inventory = IctvGenusInventory(
        (_species(0, "Coronaviridae", "Betacoronavirus", "OC43"),)
    )
    order: list[str] = []
    genus = _Genus("Alphacoronavirus", order)
    virus = _Virus({}, order)
    text = "Novel coronaviridae spp. (eg bat coronaviruses WIV1 or SHC01)"
    rows = _harmonizer(genus, virus).harmonize(
        (_row("Coronaviridae", "Betacoronavirus", text),),
        inventory,
    )
    assert order == ["virus"]
    assert rows[0].nen_genus == "Betacoronavirus"
    assert rows[0].issues == "catchall"


def test_serotype_rows_repeat_the_catalogue_virus() -> None:
    inventory = IctvGenusInventory(
        (
            _species(0, "Kolmioviridae", "Deltavirus", "hepatitis D virus 1"),
            _species(1, "Kolmioviridae", "Deltavirus", "hepatitis D virus 2"),
        )
    )
    genus = _Genus(None)
    virus = _Virus({"Deltavirus": ("hepatitis D virus 1", "hepatitis D virus 2")})
    rows = _harmonizer(genus, virus).harmonize(
        (_row("Kolmioviridae", "Deltavirus", "Hepatitis D virus"),),
        inventory,
    )
    assert [row.viruses for row in rows] == ["Hepatitis D virus", "Hepatitis D virus"]
    assert [row.nen_virus for row in rows] == [
        "hepatitis D virus 1",
        "hepatitis D virus 2",
    ]


def test_semicolon_exemplar_is_one_candidate() -> None:
    exemplar = "enterovirus E1; bovine enterovirus 1"
    inventory = IctvGenusInventory(
        (_species(0, "Picornaviridae", "Enterovirus", exemplar),)
    )
    genus = _Genus(None)
    virus = _Virus({"Enterovirus": (exemplar,)})
    rows = _harmonizer(genus, virus).harmonize(
        (_row("Picornaviridae", "Enterovirus", "bovine enterovirus"),),
        inventory,
    )
    assert len(rows) == 1
    assert rows[0].nen_virus == exemplar
    assert ";" in rows[0].nen_virus
