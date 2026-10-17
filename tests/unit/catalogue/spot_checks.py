"""Spot-check oracles from design/specs/spec.redteam.md."""

from __future__ import annotations

from virus_redteaming.catalogue.models import TableRow, VirusRecord

HANTAVIRIDAE_SPOT_CHECKS: tuple[VirusRecord, ...] = (
    VirusRecord("Hantaviridae", "Orthohantavirus", "Andes virus", "3", ""),
    VirusRecord("Hantaviridae", "Orthohantavirus", "Bayou virus", "3", ""),
    VirusRecord("Hantaviridae", "Orthohantavirus", "Black Creek Canal virus", "3", ""),
    VirusRecord("Hantaviridae", "Orthohantavirus", "Caño Delgadito virus", "3", ""),
    VirusRecord("Hantaviridae", "Orthohantavirus", "Choclo virus", "3", ""),
)

FLAVIVIRIDAE_SPOT_CHECKS: tuple[VirusRecord, ...] = (
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Absettarov virus", "3", ""),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Alkhumra haemorrhagic fever virus", "3", ""),
    VirusRecord(
        "Flaviviridae",
        "Orthoflavivirus",
        "Central European tick-borne encephalitis virus",
        "3",
        "",
    ),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Dengue virus", "3", ""),
    VirusRecord(
        "Flaviviridae",
        "Orthoflavivirus",
        "Far Eastern tick-borne encephalitis virus (formerly Russian spring–summer encephalitis virus)",
        "3",
        "",
    ),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Hanzalova virus", "3", ""),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Hypr virus", "3", ""),
    VirusRecord(
        "Flaviviridae",
        "Orthoflavivirus",
        "Israel turkey meningitis meningoencephalomyelitis virus",
        "3",
        "",
    ),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Japanese encephalitis virus", "3", ""),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Kumlinge virus", "3", ""),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Kyasanur Forest disease virus", "3", ""),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Louping ill virus", "3*", ""),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Murray Valley encephalitis virus", "3", ""),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Negishi virus", "3", ""),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Omsk haemorrhagic fever virus", "3", ""),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Powassan virus", "3", ""),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Rocio virus", "3", ""),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Sal Vieja virus", "3", ""),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "San Perlita virus", "3", ""),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Siberian tick-borne encephalitis virus", "3", ""),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Spondweni virus", "3", ""),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "St Louis encephalitis virus", "3", ""),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Usutu virus", "2", ""),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Wesselsbron virus", "3*", ""),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "West Nile fever virus", "3", ""),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Yellow fever virus", "3", ""),
    VirusRecord("Flaviviridae", "Orthoflavivirus", "Zika virus", "2", ""),
    VirusRecord(
        "Flaviviridae",
        "Orthoflavivirus",
        "Other tick-borne encephalitis viruses known to be pathogenic in humans",
        "3",
        "",
    ),
)

HANTAVIRIDAE_TABLE: tuple[TableRow, ...] = (
    TableRow("Viruses", "", ""),
    TableRow("Family Hantaviridae\nGenus Orthohantavirus", "", ""),
    TableRow("Andes virus", "3", "In the Orthohantavirus\nandesense species"),
    TableRow("Bayou virus", "3", "In the Orthohantavirus\nbayoui species"),
    TableRow("Black Creek Canal virus", "3", "In the Orthohantavirus\nnigrorivense species"),
    TableRow("Caño Delgadito virus", "3", "In the Orthohantavirus\ndelgaditoense species"),
    TableRow("Choclo virus", "3", "In the Orthohantavirus\nchocloense species"),
)

FLAVIVIRIDAE_TABLE: tuple[TableRow, ...] = (
    TableRow("Viruses", "", ""),
    TableRow("Family Flaviviridae\nGenus Orthoflavivirus", "", ""),
    TableRow(
        "Absettarov virus",
        "3",
        "Tick borne encephalitis virus\n(TBEV) – Far Eastern\nSubtype\nIn the Orthoflavivirus\nencephalitidis species",
    ),
    TableRow("Alkhumra haemorrhagic fever virus", "3", "In the Orthoflavivirus\nkyasanurense species"),
    TableRow(
        "Central European tick-borne\nencephalitis virus",
        "3",
        "Tick borne encephalitis virus\n(TBEV) – European Subtype",
    ),
    TableRow("Dengue virus", "3", "In the Orthoflavivirus\ndenguei species"),
    TableRow(
        "Far Eastern tick-borne encephalitis\nvirus (formerly Russian spring–\nsummer encephalitis virus)",
        "3",
        "Vaccine available",
    ),
    TableRow(
        "Hanzalova virus",
        "3",
        "Vaccine available\nTick borne encephalitis virus\n(TBEV) – European Subtype",
    ),
    TableRow("Hypr virus", "3", "Vaccine available"),
    TableRow("Israel turkey meningitis\nmeningoencephalomyelitis virus", "3", ""),
    TableRow("Japanese encephalitis virus", "3", "Classified under SAPO\nVaccine available"),
    TableRow("Kumlinge virus", "3", "Tick borne encephalitis virus\n(TBEV) – European Subtype"),
    TableRow("Kyasanur Forest disease virus", "3", "Vaccine available"),
    TableRow("Louping ill virus", "3*", "In the Orthoflavivirus loupingi\nspecies"),
    TableRow("Murray Valley encephalitis virus", "3", ""),
    TableRow("Negishi virus", "3", "Tick borne encephalitis virus\n(TBEV) – Far Eastern\nSubtype"),
    TableRow("Omsk haemorrhagic fever virus", "3", "Vaccine available"),
    TableRow("Powassan virus", "3", ""),
    TableRow("Rocio virus", "3", ""),
    TableRow("Sal Vieja virus", "3", ""),
    TableRow("San Perlita virus", "3", ""),
    TableRow("Siberian tick-borne encephalitis virus", "3", "Vaccine available"),
    TableRow("Spondweni virus", "3", ""),
    TableRow("St Louis encephalitis virus", "3", "Classified under SAPO"),
    TableRow("Usutu virus", "2", ""),
    TableRow("Wesselsbron virus", "3*", ""),
    TableRow("West Nile fever virus", "3", "Classified under SAPO"),
    TableRow("Yellow fever virus", "3", "Vaccine available"),
    TableRow("Zika virus", "2", ""),
    TableRow(
        "Other tick-borne encephalitis viruses\nknown to be pathogenic in humans",
        "3",
        "Tick borne encephalitis virus\n(TBEV) – European, Far-\nEastern and Siberian\nsubtypes",
    ),
)
