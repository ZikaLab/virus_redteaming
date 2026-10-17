"""Spot checks from spec.redteam.md using the Hantaviridae and Flaviviridae examples."""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from virus_redteaming.catalogue.csv_sink import LongFormatCsvWriter
from virus_redteaming.catalogue.errors import MissingVirusSectionError
from virus_redteaming.catalogue.models import CSV_COLUMNS, TableRow, VirusRecord
from virus_redteaming.catalogue.parser import ApprovedVirusListParser
from virus_redteaming.catalogue.workflow import ParseApprovedVirusList

from tests.unit.catalogue.spot_checks import (
    FLAVIVIRIDAE_SPOT_CHECKS,
    FLAVIVIRIDAE_TABLE,
    HANTAVIRIDAE_SPOT_CHECKS,
    HANTAVIRIDAE_TABLE,
)


class SequenceTableExtractor:
    def __init__(self, rows: tuple[TableRow, ...]) -> None:
        self._rows = rows

    def extract(self, pdf_path: Path) -> tuple[TableRow, ...]:
        assert pdf_path  # path is unused; the fake already holds rows
        return self._rows


class MemoryCsvSink:
    def __init__(self) -> None:
        self.records: tuple[VirusRecord, ...] = ()

    def write(self, records: tuple[VirusRecord, ...]) -> None:
        self.records = tuple(records)


def _by_virus(records: tuple[VirusRecord, ...]) -> dict[str, VirusRecord]:
    return {record.virus: record for record in records}


def _assert_spot_checks(records: tuple[VirusRecord, ...], expected: tuple[VirusRecord, ...]) -> None:
    found = _by_virus(records)
    for want in expected:
        assert want.virus in found, f"missing virus {want.virus!r}"
        got = found[want.virus]
        assert got.as_csv_tuple() == want.as_csv_tuple()


def test_wrapped_en_dash_does_not_insert_a_space() -> None:
    from virus_redteaming.catalogue.text import collapse_whitespace

    assert (
        collapse_whitespace("virus (formerly Russian spring–\nsummer encephalitis virus)")
        == "virus (formerly Russian spring–summer encephalitis virus)"
    )
    assert collapse_whitespace("(TBEV) – Far Eastern") == "(TBEV) – Far Eastern"


def test_hantaviridae_spot_checks_match_spec_examples() -> None:
    records = ApprovedVirusListParser().parse(HANTAVIRIDAE_TABLE)
    assert [record.virus for record in records] == [item.virus for item in HANTAVIRIDAE_SPOT_CHECKS]
    _assert_spot_checks(records, HANTAVIRIDAE_SPOT_CHECKS)
    for record in records:
        assert record.schedule_5 == ""


def test_flaviviridae_spot_checks_match_spec_examples() -> None:
    records = ApprovedVirusListParser().parse(FLAVIVIRIDAE_TABLE)
    _assert_spot_checks(records, FLAVIVIRIDAE_SPOT_CHECKS)


def test_absettarov_notes_are_not_merged_into_alkhumra_name() -> None:
    records = ApprovedVirusListParser().parse(FLAVIVIRIDAE_TABLE)
    names = [record.virus for record in records]
    assert "Alkhumra haemorrhagic fever virus" in names
    assert all("Alkhumra" not in name or name == "Alkhumra haemorrhagic fever virus" for name in names)
    glued = (
        "Tick borne encephalitis virus (TBEV) – Far Eastern Subtype "
        "Alkhumra haemorrhagic fever virus"
    )
    assert glued not in names


def test_hanzalova_schedule_5_mark_maps_to_section_sign() -> None:
    rows = (
        TableRow("Viruses", "", ""),
        TableRow("Family Flaviviridae\nGenus Orthoflavivirus", "", ""),
        TableRow("Hanzalova virus", "3", "Vaccine available §"),
    )
    records = _by_virus(ApprovedVirusListParser().parse(rows))
    assert records["Hanzalova virus"].schedule_5 == "§"
    assert records["Hanzalova virus"].hazard_group == "3"


def test_asterisk_stays_on_hazard_group_not_schedule_5() -> None:
    records = _by_virus(ApprovedVirusListParser().parse(FLAVIVIRIDAE_TABLE))
    assert records["Louping ill virus"].hazard_group == "3*"
    assert records["Louping ill virus"].schedule_5 == ""
    assert records["Wesselsbron virus"].hazard_group == "3*"
    assert records["Usutu virus"].hazard_group == "2"
    assert records["Zika virus"].hazard_group == "2"


def test_csv_header_and_long_format_hantaviridae() -> None:
    buffer = StringIO()
    LongFormatCsvWriter.write_to(LongFormatCsvWriter(Path("unused.csv")), buffer, HANTAVIRIDAE_SPOT_CHECKS)
    rows = list(csv.reader(StringIO(buffer.getvalue())))
    assert rows[0] == list(CSV_COLUMNS)
    assert rows[0][-1] == "schedule 5"
    body = rows[1:]
    assert body[0] == ["Hantaviridae", "Orthohantavirus", "Andes virus", "3", ""]
    assert body[4] == ["Hantaviridae", "Orthohantavirus", "Choclo virus", "3", ""]


def test_page_chrome_and_annex_are_ignored() -> None:
    rows = (
        TableRow("L-type BSE agent", "3*", ""),
        TableRow("Viruses", "", ""),
        TableRow("Family Adenoviridae", "", ""),
        TableRow("Biological agent", "", "Taxonomy / notes"),
        TableRow("", "Human pathogen", ""),
        TableRow("", "hazard group", ""),
        TableRow("Adenoviridae spp. known to be\npathogenic in humans", "2", ""),
        TableRow("Annex 1: Biological agents\nwhich may be used at less", "", ""),
        TableRow("Chikungunya virus", "3*", ""),
    )
    records = ApprovedVirusListParser().parse(rows)
    assert len(records) == 1
    assert records[0].virus == "Adenoviridae spp. known to be pathogenic in humans"
    assert records[0].family == "Adenoviridae"
    assert records[0].genus == ""


def test_sticky_genus_change_inside_a_family() -> None:
    rows = (
        TableRow("Viruses", "", ""),
        TableRow("Family Flaviviridae\nGenus Orthoflavivirus", "", ""),
        TableRow("Zika virus", "2", ""),
        TableRow("Genus Hepacivirus", "", ""),
        TableRow("Hepatitis C virus, HCV, (also known\nas Hepacivirus C virus)", "3*", ""),
    )
    records = ApprovedVirusListParser().parse(rows)
    assert records[0].genus == "Orthoflavivirus"
    assert records[1].family == "Flaviviridae"
    assert records[1].genus == "Hepacivirus"
    assert records[1].hazard_group == "3*"


def test_missing_viruses_heading_raises() -> None:
    try:
        ApprovedVirusListParser().parse((TableRow("Andes virus", "3", ""),))
    except MissingVirusSectionError:
        return
    raise AssertionError("expected MissingVirusSectionError")


def test_workflow_injects_extractor_parser_and_sink() -> None:
    sink = MemoryCsvSink()
    count = ParseApprovedVirusList(
        extractor=SequenceTableExtractor(HANTAVIRIDAE_TABLE),
        parser=ApprovedVirusListParser(),
        sink=sink,
    ).run(Path("/tmp/unused.pdf"))
    assert count == 5
    _assert_spot_checks(sink.records, HANTAVIRIDAE_SPOT_CHECKS)
