"""The published merge sort: genus, hazard group, then Schedule 5."""

import pytest

from virus_redteaming.hse_cat1_merge.errors import MergeSortError
from virus_redteaming.hse_cat1_merge.models import MergedVirusRow
from virus_redteaming.hse_cat1_merge.order import (
    GENUS_COLUMN,
    HAZARD_COLUMN,
    HAZARD_DESCENDING,
    SCHEDULE_COLUMN,
    SCHEDULE_DESCENDING,
    MergedTableOrder,
)


def _row(
    *,
    ictv_genus: str = "Alphavirus",
    hazard_group: str = "2",
    schedule_5: str = "0",
    ictv_virus: str = "virus",
) -> MergedVirusRow:
    return MergedVirusRow(
        source="HSE",
        catalogue_family="",
        catalogue_genus="",
        catalogue_virus="",
        ictv_family="",
        ictv_genus=ictv_genus,
        ictv_virus=ictv_virus,
        species="",
        kingdom="",
        genbank_accessions="",
        ncbi_accession="",
        refseq_accessions="",
        hazard_group=hazard_group,
        schedule_5=schedule_5,
        issues="",
    )


def test_sort_command_names_its_columns_and_directions() -> None:
    assert GENUS_COLUMN == "ICTV genus"
    assert HAZARD_COLUMN == "Human pathogen hazard group"
    assert SCHEDULE_COLUMN == "Schedule 5"
    assert HAZARD_DESCENDING == ("4", "3*", "3", "2", "1")
    assert SCHEDULE_DESCENDING == ("1", "0")


def test_sort_key_is_genus_then_hazard_then_schedule_then_position() -> None:
    order = MergedTableOrder()
    row = _row(ictv_genus="Alphavirus", hazard_group="3*", schedule_5="1")
    assert order.sort_key(row, 7) == ("Alphavirus", 1, 0, 7)


def test_hazard_rank_descends_from_4_through_3_star_to_1() -> None:
    order = MergedTableOrder()
    ranks = [
        order.sort_key(_row(hazard_group=value), 0)[1] for value in HAZARD_DESCENDING
    ]
    assert ranks == [0, 1, 2, 3, 4]


def test_schedule_rank_puts_1_before_0() -> None:
    order = MergedTableOrder()
    ranks = [
        order.sort_key(_row(schedule_5=value), 0)[2] for value in SCHEDULE_DESCENDING
    ]
    assert ranks == [0, 1]


def test_genus_sorts_from_a_to_z_with_a_blank_genus_first() -> None:
    order = MergedTableOrder()
    blank = order.sort_key(_row(ictv_genus=""), 0)[0]
    alpha = order.sort_key(_row(ictv_genus="Alphavirus"), 0)[0]
    ortho = order.sort_key(_row(ictv_genus="Orthoflavivirus"), 0)[0]
    assert blank < alpha < ortho


def test_sort_applies_genus_before_hazard_before_schedule() -> None:
    specs = (
        ("Betavirus", "4", "1", "beta"),
        ("Alphavirus", "1", "0", "low"),
        ("Alphavirus", "4", "0", "sched0"),
        ("Alphavirus", "4", "1", "sched1"),
        ("Alphavirus", "3*", "1", "star"),
        ("Alphavirus", "3", "0", "three"),
        ("", "2", "0", "blank"),
        ("Alphavirus", "2", "1", "first"),
        ("Alphavirus", "2", "1", "second"),
    )
    rows = tuple(
        _row(
            ictv_genus=genus,
            hazard_group=hazard,
            schedule_5=schedule,
            ictv_virus=virus,
        )
        for genus, hazard, schedule, virus in specs
    )
    ordered = [row.ictv_virus for row in MergedTableOrder().sort(rows)]
    assert ordered == [
        "blank",
        "sched1",
        "sched0",
        "star",
        "three",
        "first",
        "second",
        "low",
        "beta",
    ]


def test_equal_keys_keep_the_unsorted_stack_order() -> None:
    rows = (
        _row(ictv_virus="earlier"),
        _row(ictv_virus="later"),
    )
    ordered = MergedTableOrder().sort(rows)
    assert [row.ictv_virus for row in ordered] == ["earlier", "later"]
    assert ordered[0] is rows[0]


def test_unknown_hazard_group_is_rejected() -> None:
    with pytest.raises(MergeSortError, match="Human pathogen hazard group"):
        MergedTableOrder().sort_key(_row(hazard_group="5"), 0)


def test_unknown_schedule_5_is_rejected() -> None:
    with pytest.raises(MergeSortError, match="Schedule 5"):
        MergedTableOrder().sort_key(_row(schedule_5="2"), 0)
