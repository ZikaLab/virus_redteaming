"""Waves of twenty share one prepared ``.tmp`` and keep table order."""

import threading
import time
from pathlib import Path

from tests.unit.claude_harness.fakes import MemoryWriter, row
from virus_redteaming.claude_harness.models import RedTeamResult, RedTeamRow
from virus_redteaming.claude_harness.sequence import FastaSequence
from virus_redteaming.claude_harness.source import MergedRedTeamSource
from virus_redteaming.claude_harness.workflow import (
    ClaudePing,
    RedTeamBatch,
    RedTeamExchange,
)


class _Prepare:
    def __init__(self, missing: set[str] | None = None) -> None:
        self.calls: list[str] = []
        self.missing = missing or set()

    def prepare(self, accession: str) -> Path | None:
        self.calls.append(accession)
        if accession in self.missing:
            return None
        return Path(f"{accession}.tmp")


class _Source:
    def __init__(self, rows: tuple[RedTeamRow, ...]) -> None:
        self._rows = rows

    def read(self) -> tuple[RedTeamRow, ...]:
        return self._rows


def _result(item: RedTeamRow, response: str = "10") -> RedTeamResult:
    return RedTeamResult(
        virus=item.virus,
        claude_response=response,
        family=item.family,
        genus=item.genus,
        hazard_group=item.hazard_group,
        schedule_5=item.schedule_5,
        secondary_structure=".",
    )


class _Exchange:
    def __init__(self, delay_first: bool = False) -> None:
        self.seen: list[str] = []
        self._delay_first = delay_first
        self._lock = threading.Lock()

    def run(self, item: RedTeamRow) -> RedTeamResult:
        accession = item.accession
        if self._delay_first and accession == "A00":
            time.sleep(0.05)
        with self._lock:
            self.seen.append(accession)
        return _result(item, accession)


def test_shared_accession_prepares_one_tmp_before_the_wave() -> None:
    prepared = _Prepare()
    writer = MemoryWriter()
    rows = tuple(row(virus=f"flu-{index}", accession="V00603") for index in range(6))
    RedTeamBatch(_Source(rows), prepared, _Exchange(), writer, width=20).run()
    assert prepared.calls == ["V00603"]
    assert writer.rows is not None
    assert len(writer.rows) == 6


def test_wave_of_twenty_runs_together() -> None:
    barrier = threading.Barrier(20)
    seen: list[str] = []
    lock = threading.Lock()

    class _Chat:
        def complete(self, prompt: str, file_id: str | None = None) -> str:
            if "Count the number" in prompt:
                barrier.wait(timeout=5)
                with lock:
                    seen.append(file_id or "")
                if file_id == "file_A00":
                    time.sleep(0.02)
            return "10"

    class _Store:
        def upload(self, accession: str) -> str:
            return f"file_{accession}"

        def delete(self, file_id: str) -> None:
            return None

    from virus_redteaming.claude_harness.prompt import SequencePrompt

    rows = tuple(
        row(virus=f"A{index:02d}", accession=f"A{index:02d}") for index in range(20)
    )
    writer = MemoryWriter()
    exchange = RedTeamExchange(
        ClaudePing(_Chat()),
        _Store(),
        SequencePrompt(),
        Path("."),
    )
    RedTeamBatch(_Source(rows), _Prepare(), exchange, writer, width=20).run()
    assert len(seen) == 20
    assert writer.rows is not None
    assert [item.virus for item in writer.rows] == [
        f"A{index:02d}" for index in range(20)
    ]


def test_last_wave_runs_the_remainder_together(monkeypatch: object) -> None:
    called = {"layer": False}

    def _boom(self: ClaudePing, layer: object, prompts: object) -> tuple[str, ...]:
        called["layer"] = True
        raise AssertionError(layer)

    monkeypatch.setattr(ClaudePing, "run_layer", _boom)  # type: ignore[arg-type]
    rows = tuple(
        row(virus=str(index), accession=f"A{index:02d}") for index in range(21)
    )
    exchange = _Exchange()
    writer = MemoryWriter()
    RedTeamBatch(_Source(rows), _Prepare(), exchange, writer, width=20).run()
    assert called["layer"] is False
    assert len(exchange.seen) == 21
    assert writer.rows is not None
    assert len(writer.rows) == 21


def test_named_row_without_accession_writes_no_sequence() -> None:
    writer = MemoryWriter()
    exchange = _Exchange()
    rows = (row(virus="human bocavirus 3", accession=""),)
    RedTeamBatch(_Source(rows), _Prepare(), exchange, writer, width=20).run()
    assert exchange.seen == []
    assert writer.rows is not None
    assert writer.rows[0].claude_response == "no sequence"


def test_missing_fasta_writes_no_sequence_without_a_call(tmp_path: Path) -> None:
    writer = MemoryWriter()
    exchange = _Exchange()
    rows = (row(accession="MISSING"),)
    RedTeamBatch(
        _Source(rows),
        FastaSequence(tmp_path, tmp_path / "sequences"),
        exchange,
        writer,
        width=20,
    ).run()
    assert exchange.seen == []
    assert writer.rows is not None
    assert writer.rows[0].claude_response == "no sequence"


def test_repeated_first_code_is_sent_again() -> None:
    class _Counting:
        def __init__(self) -> None:
            self.n = 0
            self._lock = threading.Lock()

        def complete(self, prompt: str, file_id: str | None = None) -> str:
            with self._lock:
                self.n += 1
                return str(self.n)

    class _Store:
        def upload(self, accession: str) -> str:
            return "file"

        def delete(self, file_id: str) -> None:
            return None

    from virus_redteaming.claude_harness.prompt import SequencePrompt

    chat = _Counting()
    writer = MemoryWriter()
    rows = (row(virus="one"), row(virus="two"))
    exchange = RedTeamExchange(ClaudePing(chat), _Store(), SequencePrompt(), Path("."))
    RedTeamBatch(_Source(rows), _Prepare(), exchange, writer, width=20).run()
    assert writer.rows is not None
    assert writer.rows[0].claude_response != writer.rows[1].claude_response


def test_blank_key_and_accession_are_skipped(tmp_path: Path) -> None:
    table = tmp_path / "t.csv"
    table.write_text(
        "ICTV virus,NCBI accession,ICTV family,ICTV genus,"
        "Human pathogen hazard group,Schedule 5\n"
        ",,,,,\n",
        encoding="utf-8",
    )
    writer = MemoryWriter()
    RedTeamBatch(
        MergedRedTeamSource(table),
        _Prepare(),
        _Exchange(),
        writer,
        width=20,
    ).run()
    assert writer.rows == ()


def test_each_wave_is_written_before_the_run_finishes() -> None:
    class _Writer:
        def __init__(self) -> None:
            self.calls: list[int] = []

        def write(self, rows: tuple[RedTeamResult, ...]) -> None:
            self.calls.append(len(rows))

    writer = _Writer()
    rows = tuple(
        row(virus=str(index), accession=f"A{index:02d}") for index in range(21)
    )
    RedTeamBatch(_Source(rows), _Prepare(), _Exchange(), writer, width=20).run()
    assert writer.calls == [20, 21, 21]
