"""Real catalogue and ICTV file. Prompts are the deterministic test double."""

from __future__ import annotations

import csv
import re
from pathlib import Path

from virus_redteaming.category1.candidates import GenusCandidateList
from virus_redteaming.category1.except_sample import (
    GenusCategory1Sampler,
    GenusVirusExcept,
)
from virus_redteaming.category1.harmonize import NenHarmonizer
from virus_redteaming.category1.inventory import CatalogueGenusIndex, IctvGenusInventory
from virus_redteaming.category1.models import CatalogueVirus, NenRow
from virus_redteaming.category1.workflow import BuildCategory1
from virus_redteaming.category1.write import IctvCat1Writer, NenReader, NenWriter

ROOT = Path(__file__).resolve().parents[2]
VIRUSES_CSV = ROOT / "output" / "viruses.csv"
ICTV_CSV = ROOT / "docs" / "ICTV_RNA_virus_species_MSL41.csv"
ICTV_ROWS = 7230
CATALOGUE_ROWS = 232

_INNER_PAREN = re.compile(r"\([^()]*\)")
_LOCKED: tuple[tuple[str, str], ...] = (
    ("Zaire ebolavirus", "Ebola virus"),
    ("Bundibugyo ebolavirus", "Bundibugyo virus"),
    ("Reston ebolavirus", "Reston virus"),
    ("Sudan ebolavirus", "Sudan virus"),
    ("Tai Forest ebolavirus", "Taï Forest virus"),
    ("St Louis encephalitis virus", "St. Louis encephalitis virus"),
    ("Far Eastern tick-borne encephalitis virus", "tick-borne encephalitis virus 1"),
    (
        "Central European tick-borne encephalitis virus",
        "tick-borne encephalitis virus 2",
    ),
)
_NON_RNA_GENERA = frozenset(
    {
        "Alphatorquevirus",
        "Betapolyomavirus",
        "Bocaparvovirus",
        "Cytomegalovirus",
        "Deltaretrovirus",
        "Erythroparvovirus",
        "Gammaretrovirus",
        "Lentivirus",
        "Lymphocryptovirus",
        "Molluscipoxvirus",
        "Orthohepadnavirus",
        "Orthopoxvirus",
        "Parapoxvirus",
        "Rhadinovirus",
        "Roseolavirus",
        "Simplex virus",
        "Tetraparvovirus",
        "Varicellovirus",
        "Yatapoxvirus",
    }
)
_SHORT_GENERA = frozenset(
    {
        "Alphainfluenzavirus",
        "Betainfluenzavirus",
        "Deltainfluenzavirus",
        "Gammainfluenzavirus",
        "Norovirus",
        "Orthomarburgvirus",
        "Deltavirus",
    }
)


def _strip(text: str) -> str:
    current = text
    while True:
        updated = _INNER_PAREN.sub("", current)
        if updated == current:
            break
        current = updated
    open_at = current.find("(")
    if open_at != -1:
        current = current[:open_at]
    if current.endswith(")"):
        current = current[:-1]
    lowered = current.casefold()
    cut_at: int | None = None
    for marker in (" also known as", " formerly"):
        at = lowered.find(marker)
        if at != -1 and (cut_at is None or at < cut_at):
            cut_at = at
    if cut_at is not None:
        current = current[:cut_at]
    return " ".join(current.split()).casefold()


def _probes(virus: str) -> tuple[str, ...]:
    stripped = _strip(virus)
    found = [stripped]
    if "," in stripped:
        found.append(stripped.split(",", 1)[0].strip())
    extra: list[str] = []
    for probe in found:
        if "haemorrhagic" in probe:
            extra.append(probe.replace("haemorrhagic", "hemorrhagic"))
        if "hemorrhagic" in probe:
            extra.append(probe.replace("hemorrhagic", "haemorrhagic"))
    return tuple(found + extra)


class EndToEndGenusPrompt:
    def choose(self, row: CatalogueVirus, candidates: tuple[str, ...]) -> str | None:
        if row.genus == "Ortonairovirus" and "Orthonairovirus" in candidates:
            return "Orthonairovirus"
        if row.genus == "Hepacivirus" and "Orthohepacivirus" in candidates:
            return "Orthohepacivirus"
        astro = row.genus == "" and row.family == "Astroviridae"
        if astro and "Mamastrovirus" in candidates:
            return "Mamastrovirus"
        if "Sapporo virus" in row.virus and "Sapovirus" in candidates:
            return "Sapovirus"
        return None


class EndToEndVirusPrompt:
    def choose(
        self,
        nen_genus: str,
        virus: str,
        exemplars: tuple[str, ...],
    ) -> tuple[str, ...]:
        if "Astroviridae spp." in virus:
            if "mamastrovirus 1" in exemplars:
                return ("mamastrovirus 1",)
            return ()
        if nen_genus == "Alphainfluenzavirus" and "influenza A virus" in exemplars:
            return ("influenza A virus",)
        probes = _probes(virus)
        locked = {exemplar for needle, exemplar in _LOCKED if needle in virus}
        kept: list[str] = []
        for exemplar in exemplars:
            folded = exemplar.casefold()
            matched = any(
                folded == probe or folded.startswith(probe + " ") for probe in probes
            )
            if matched or exemplar in locked:
                kept.append(exemplar)
        return tuple(kept)


def _run(tmp_path: Path) -> tuple[Path, Path]:
    nen = tmp_path / "nen_viruses.csv"
    out = tmp_path / "ICTV_cat1.csv"
    BuildCategory1(
        catalogue_index=CatalogueGenusIndex(),
        harmonizer=NenHarmonizer(
            GenusCandidateList(),
            EndToEndGenusPrompt(),
            EndToEndVirusPrompt(),
        ),
        exceptor=GenusVirusExcept(),
        sampler=GenusCategory1Sampler(),
        nen_writer=NenWriter(),
        nen_reader=NenReader(),
        cat1_writer=IctvCat1Writer(),
    ).run(VIRUSES_CSV, ICTV_CSV, nen, out, refresh=True)
    return nen, out


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_sources_stay_at_locked_counts(tmp_path: Path) -> None:
    before = (VIRUSES_CSV.read_bytes(), ICTV_CSV.read_bytes())
    _run(tmp_path)
    assert before == (VIRUSES_CSV.read_bytes(), ICTV_CSV.read_bytes())
    assert sum(1 for _ in ICTV_CSV.open(encoding="utf-8")) - 1 == ICTV_ROWS
    assert sum(1 for _ in VIRUSES_CSV.open(encoding="utf-8")) - 1 == CATALOGUE_ROWS


def test_locked_nen_genus_rows(tmp_path: Path) -> None:
    nen_path, _out = _run(tmp_path)
    nen = NenReader().read(nen_path)
    orto = [row for row in nen if row.genus == "Ortonairovirus"]
    assert len(orto) == 5
    assert {row.nen_genus for row in orto} == {"Orthonairovirus"}
    hepatitis_c = [row for row in nen if "Hepatitis C virus" in row.viruses]
    assert {row.nen_genus for row in hepatitis_c} == {"Orthohepacivirus"}
    sapporo = [row for row in nen if "Sapporo virus" in row.viruses]
    assert [(row.nen_genus, row.nen_virus) for row in sapporo] == [
        ("Sapovirus", "Sapporo virus")
    ]
    norwalk = [row for row in nen if "Norwalk virus" in row.viruses]
    assert {row.nen_genus for row in norwalk} == {"Norovirus"}
    astro = [row for row in nen if row.family == "Astroviridae" and row.genus == ""]
    assert [(row.nen_genus, row.nen_virus) for row in astro] == [
        ("Mamastrovirus", "mamastrovirus 1")
    ]


def test_dengue_is_only_type_2(tmp_path: Path) -> None:
    nen_path, out = _run(tmp_path)
    dengue = [
        row for row in NenReader().read(nen_path) if row.viruses == "Dengue virus"
    ]
    assert [row.nen_virus for row in dengue] == ["dengue virus type 2"]
    flavivirus = [
        row["Exemplar virus"] for row in _rows(out) if row["Genus"] == "Orthoflavivirus"
    ]
    assert "dengue virus type 2" not in flavivirus


def test_cat1_rows_are_category_1_constants(tmp_path: Path) -> None:
    _nen, out = _run(tmp_path)
    inventory = IctvGenusInventory.from_csv(ICTV_CSV)
    genera = set(inventory.genera())
    rows = _rows(out)
    assert rows
    for row in rows:
        assert row["Human pathogen hazard group"] == "1"
        assert row["Schedule 5"] == "0"
        assert row["Issues"] == ""
        assert row["Genus"] in genera


def test_non_rna_genera_are_absent_from_the_sample(tmp_path: Path) -> None:
    nen_path, out = _run(tmp_path)
    assert not any(row["Genus"] in _NON_RNA_GENERA for row in _rows(out))
    for row in NenReader().read(nen_path):
        blank_dna = row.genus == "" and row.family in {
            "Adenoviridae",
            "Papillomaviridae",
        }
        if row.genus in _NON_RNA_GENERA or blank_dna:
            assert row.nen_genus == ""
            assert row.issues == "genus not in ICTV"


def test_orthobunyavirus_sample_is_the_source_prefix(tmp_path: Path) -> None:
    nen_path, out = _run(tmp_path)
    nen = NenReader().read(nen_path)
    inventory = IctvGenusInventory.from_csv(ICTV_CSV)
    genus = "Orthobunyavirus"
    count = len({row.catalogue_index for row in nen if row.nen_genus == genus})
    remainder = GenusVirusExcept().remainder(inventory, nen)[genus][:count]
    actual = [row["Exemplar virus"] for row in _rows(out) if row["Genus"] == genus]
    assert actual == [species.exemplar for species in remainder]


def test_orthoebolavirus_sample_is_bombali_only(tmp_path: Path) -> None:
    nen_path, out = _run(tmp_path)
    expected = {
        "Zaire ebolavirus": "Ebola virus",
        "Bundibugyo ebolavirus": "Bundibugyo virus",
        "Reston ebolavirus": "Reston virus",
        "Sudan ebolavirus": "Sudan virus",
        "Tai Forest ebolavirus": "Taï Forest virus",
    }
    found: dict[str, str] = {}
    for row in NenReader().read(nen_path):
        for needle, exemplar in expected.items():
            if needle in row.viruses:
                found[needle] = row.nen_virus
                assert row.nen_virus == exemplar
    assert set(found) == set(expected)
    ebola = [
        row["Exemplar virus"]
        for row in _rows(out)
        if row["Genus"] == "Orthoebolavirus"
    ]
    assert ebola == ["Bombali virus"]


def test_tick_borne_encephalitis_exemplars_are_removed(tmp_path: Path) -> None:
    nen_path, out = _run(tmp_path)
    nen = NenReader().read(nen_path)
    far = [
        row.nen_virus
        for row in nen
        if "Far Eastern tick-borne encephalitis virus" in row.viruses
    ]
    central = [
        row.nen_virus
        for row in nen
        if "Central European tick-borne encephalitis virus" in row.viruses
    ]
    assert far == ["tick-borne encephalitis virus 1"]
    assert central == ["tick-borne encephalitis virus 2"]
    exemplars = {row["Exemplar virus"] for row in _rows(out)}
    assert "tick-borne encephalitis virus 1" not in exemplars
    assert "tick-borne encephalitis virus 2" not in exemplars


def test_short_genera_contribute_no_category_1_rows(tmp_path: Path) -> None:
    nen_path, out = _run(tmp_path)
    assert not any(row["Genus"] in _SHORT_GENERA for row in _rows(out))
    nen: tuple[NenRow, ...] = NenReader().read(nen_path)
    influenza = [row for row in nen if row.genus == "Alphainfluenzavirus"]
    assert len(influenza) == 6
    assert {row.nen_virus for row in influenza} == {"influenza A virus"}
    hepatitis_d = {row.nen_virus for row in nen if "Hepatitis D virus" in row.viruses}
    assert hepatitis_d == {f"hepatitis D virus {index}" for index in range(1, 9)}
