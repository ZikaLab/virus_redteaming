"""Decide whether a catalogue virus name interacts with a schedule-5 name."""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")
_ALIAS = re.compile(
    r"(?:also known as|formerly known as|formerly)\s+(.+?)(?:\)|$)",
    re.IGNORECASE,
)

# spec.schedule5.md §3.2. Compared after normalisation of both sides.
_SYNONYM_PAIRS: tuple[tuple[str, str], ...] = (
    ("Junin virus", "Argentinian mammarenavirus (also known as Junin virus)"),
    ("Sabia virus", "Brazilian mammarenavirus (also known as Sabiá virus)"),
    ("Dengue fever virus", "Dengue virus"),
    ("Lassa fever virus", "Lassa virus"),
    ("Kyasanur Forest virus", "Kyasanur Forest disease virus"),
    (
        "Congo-crimean haemorrhagic fever virus",
        "Crimean-Congo haemorrhagic fever virus",
    ),
    (
        "Dobrava/Belgrade virus",
        "Dobrava-Belgrade virus (formerly known as Belgrade (Dobrava) virus)",
    ),
    ("Hendra virus (Equine morbillivirus)", "Hendra virus"),
    (
        "Herpes simiae (B virus)",
        "Herpes B virus also known as Macacine alphaherpesvirus 1 (formerly Herpesvirus simiae)",
    ),
    ("Monkey pox virus", "Mpox virus (formerly known as Monkeypox virus)"),
    ("Middleburg virus", "Middelburg virus"),
    ("Variola virus", "Variola virus (major and minor)"),
    (
        "Lymphocytic choriomeningitis virus",
        "Lymphocytic choriomeningitis virus LCMV (all strains other than Armstrong)",
    ),
    (
        "Lymphocytic choriomeningitis virus",
        "Lymphocytic choriomeningitis virus LCMV (Armstrong strain)",
    ),
)


class VirusNameNormaliser:
    def normalise(self, text: str) -> str:
        compatibility = unicodedata.normalize("NFKC", text)
        without_marks = "".join(
            character
            for character in unicodedata.normalize("NFD", compatibility)
            if unicodedata.category(character) != "Mn"
        )
        folded = without_marks.casefold()
        for separator in ("/", "_", "–", "—"):
            folded = folded.replace(separator, "-")
        return _WHITESPACE.sub(" ", folded).strip()


class VirusNameInteractor:
    def __init__(self, normaliser: VirusNameNormaliser) -> None:
        self._normaliser = normaliser
        self._synonyms = {
            (normaliser.normalise(schedule_name), normaliser.normalise(virus_name))
            for schedule_name, virus_name in _SYNONYM_PAIRS
        }

    def interacts(self, virus_cell: str, schedule_names: tuple[str, ...]) -> bool:
        return bool(self.matched_names(virus_cell, schedule_names))

    def matched_names(self, virus_cell: str, schedule_names: tuple[str, ...]) -> frozenset[str]:
        normalised_virus = self._normaliser.normalise(virus_cell)
        if "spp." in normalised_virus or normalised_virus.startswith("other "):
            return frozenset()
        aliases = {
            self._normaliser.normalise(match.group(1))
            for match in _ALIAS.finditer(virus_cell)
        }
        hits: set[str] = set()
        for name in schedule_names:
            normalised_name = self._normaliser.normalise(name)
            if self._matches(name, normalised_name, normalised_virus, aliases):
                hits.add(name)
        return frozenset(hits)

    def _matches(
        self,
        name: str,
        normalised_name: str,
        normalised_virus: str,
        aliases: set[str],
    ) -> bool:
        if normalised_virus == normalised_name:
            return True
        if len(normalised_name) >= 6 and (
            normalised_name in normalised_virus or normalised_virus in normalised_name
        ):
            return True
        if normalised_name in aliases:
            return True
        if (normalised_name, normalised_virus) in self._synonyms:
            return True
        if name == "Ebola virus" and "ebola" in normalised_virus:
            return True
        if name == "Polio virus" and normalised_virus.startswith("poliovirus"):
            return True
        if (
            name == "SARS Coronavirus"
            and "sars-cov-1" in normalised_virus
            and "sars-cov-2" not in normalised_virus
        ):
            return True
        if name == "Influenza viruses (pandemic strains)" and "pandemic" in normalised_virus:
            return True
        return name.startswith("Tick-borne encephalitis virus") and (
            "far eastern tick-borne" in normalised_virus or "russian spring" in normalised_virus
        )
