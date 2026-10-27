"""Run the one-node Claude ping on one chain or on a whole layer."""

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import cast

from virus_redteaming.claude_harness.errors import (
    ChainCountError,
    EmptyClaudeReplyError,
    redact_client_error,
)
from virus_redteaming.claude_harness.graph import PingState, build_ping_graph
from virus_redteaming.claude_harness.layers import HarnessLayer
from virus_redteaming.claude_harness.models import RedTeamResult, RedTeamRow
from virus_redteaming.claude_harness.prompt import SequencePrompt
from virus_redteaming.claude_harness.protocols import ChatTurn, RunLog, SequenceStore
from virus_redteaming.claude_harness.sequence import FastaSequence, prepared_name
from virus_redteaming.claude_harness.sink import RedTeamReportWriter
from virus_redteaming.claude_harness.source import MergedRedTeamSource
from virus_redteaming.core.errors import VirusRedteamingError


class ClaudePing:
    """Compile the one-node graph and run it under a :class:`HarnessLayer`.

    ``run`` is one chain: one prompt, one invoke, one reply. ``run_layer``
    repeats that chain as many times as the layer allows.

    ``HarnessLayer.TEST`` calls ``run`` once, on this thread. A failure
    raises here, with no thread pool around it.

    ``HarnessLayer.TEST_PARALLEL`` and ``HarnessLayer.LIVE`` each start
    twenty chains. A pool of twenty workers runs them together. ``map`` keeps
    reply order equal to prompt order, even when a later chain finishes
    first. The first chain that raises stops the result; the other workers
    are left to finish, and that exception propagates to the caller.
    """

    def __init__(self, chat: ChatTurn) -> None:
        self._app = build_ping_graph(chat).compile()

    def run(self, prompt: str, file_id: str | None = None) -> str:
        """Run one chain and return a non-empty reply.

        This is the only path ``HarnessLayer.TEST`` uses. The parallel
        layers call it once per prompt, each call on its own worker.
        Every call invokes the compiled graph with a fresh state, so
        chains do not share a reply. ``file_id`` is omitted for a ping.
        """
        state: PingState = {"prompt": prompt, "reply": ""}
        if file_id is not None:
            state["file_id"] = file_id
        result = cast(PingState, self._app.invoke(state))
        reply = result["reply"]
        if not reply.strip():
            raise EmptyClaudeReplyError("Claude returned an empty reply")
        return reply

    def run_layer(self, layer: HarnessLayer, prompts: Sequence[str]) -> tuple[str, ...]:
        """Run ``prompts`` under ``layer`` and return the replies in order.

        ``len(prompts)`` must equal ``layer.chain_count()``. ``TEST``
        requires one prompt. ``TEST_PARALLEL`` and ``LIVE`` require twenty.
        A mismatch raises :class:`ChainCountError` and starts no chains.

        ``TEST`` runs that single prompt on the caller thread. The other
        two layers use a thread pool whose size is the chain count, so
        twenty calls are in flight together. Pass a fake ``ChatTurn`` from
        unit tests. Pass ``AnthropicChat`` for ``LIVE``, and for
        ``TEST_PARALLEL`` when running the Haiku batch.
        """
        expected = layer.chain_count()
        if len(prompts) != expected:
            noun = "chain" if expected == 1 else "chains"
            raise ChainCountError(
                f"{layer.value} runs {expected} {noun}, received {len(prompts)} prompts"
            )
        if expected == 1:
            return (self.run(prompts[0]),)
        with ThreadPoolExecutor(max_workers=expected) as pool:
            return tuple(pool.map(self.run, prompts))


def _result(row: RedTeamRow, response: str, structure: str) -> RedTeamResult:
    return RedTeamResult(
        virus=row.virus,
        claude_response=response,
        family=row.family,
        genus=row.genus,
        hazard_group=row.hazard_group,
        schedule_5=row.schedule_5,
        secondary_structure=structure,
    )


def _count_cell(reply: str) -> str:
    stripped = reply.strip()
    if stripped.isdecimal():
        return stripped
    for line in reply.splitlines():
        if line.strip():
            return line.strip()
    return "no response"


class _SilentLog:
    def line(self, text: str) -> None:
        return None


class RedTeamExchange:
    """One accession: upload, count, then secondary structure."""

    def __init__(
        self,
        ping: ClaudePing,
        store: SequenceStore,
        prompts: SequencePrompt,
        directory: Path,
        log: RunLog | None = None,
    ) -> None:
        self._ping = ping
        self._store = store
        self._prompts = prompts
        self._directory = directory
        self._log = _SilentLog() if log is None else log

    def run(self, row: RedTeamRow) -> RedTeamResult:
        """Send both prompts for ``row`` and delete the remote file."""
        file_id: str | None = None
        accession = row.accession
        path = self._directory / prepared_name(accession)
        hidden = (str(path),)
        try:
            self._log.line(
                f"{accession}: uploading {path} as sequence.txt with the count prompt"
            )
            try:
                file_id = self._store.upload(accession)
            except Exception as exc:
                detail = redact_client_error(exc, hidden)
                self._log.line(f"{accession}: upload failed:\n{detail}")
                return _result(row, detail, "")
            try:
                count = self._ping.run(self._prompts.count(), file_id=file_id)
            except (EmptyClaudeReplyError, TimeoutError) as exc:
                detail = redact_client_error(exc, hidden)
                self._log.line(f"{accession}: count failed:\n{detail}")
                return _result(row, "no response", "")
            except Exception as exc:
                detail = redact_client_error(exc, hidden)
                self._log.line(f"{accession}: count failed:\n{detail}")
                return _result(row, detail, "")
            response = _count_cell(count)
            self._log.line(f"{accession}: count reply:\n{count}")
            self._log.line(f"{accession}: structure prompt sent with the same file")
            try:
                structure = self._ping.run(self._prompts.structure(), file_id=file_id)
            except (EmptyClaudeReplyError, TimeoutError) as exc:
                detail = redact_client_error(exc, hidden)
                self._log.line(f"{accession}: structure failed:\n{detail}")
                return _result(row, response, "no response")
            except Exception as exc:
                detail = redact_client_error(exc, hidden)
                self._log.line(f"{accession}: structure failed:\n{detail}")
                return _result(row, response, detail)
            self._log.line(f"{accession}: structure reply:\n{structure}")
            return _result(row, response, structure)
        finally:
            if file_id is not None:
                try:
                    self._store.delete(file_id)
                except Exception as exc:
                    detail = redact_client_error(exc, hidden)
                    self._log.line(f"{accession}: remote file delete failed:\n{detail}")


class RedTeamBatch:
    """Run accession chains in waves. ``run_layer`` is not used."""

    def __init__(
        self,
        source: MergedRedTeamSource,
        fasta: FastaSequence,
        exchange: RedTeamExchange,
        writer: RedTeamReportWriter,
        width: int,
        log: RunLog | None = None,
    ) -> None:
        self._source = source
        self._fasta = fasta
        self._exchange = exchange
        self._writer = writer
        self._width = width
        self._log = _SilentLog() if log is None else log

    def run(self) -> None:
        """Read the table, run every wave, and replace the output CSV."""
        rows = self._source.read()
        accession_rows = sum(1 for row in rows if row.accession)
        wave_total = (
            (accession_rows + self._width - 1) // self._width if accession_rows else 0
        )
        self._log.line(f"claude-red-team: {len(rows)} rows")
        self._log.line(f"claude-red-team: {self._width} parallel chains")
        self._log.line(f"claude-red-team: {wave_total} waves")
        slots: list[RedTeamResult | None] = [None] * len(rows)
        wave: list[tuple[int, RedTeamRow]] = []
        wave_number = 0
        for index, row in enumerate(rows):
            if row.accession == "":
                slots[index] = _result(row, "no sequence", "")
                self._log.line("blank accession: no sequence, Claude not called")
                self._flush(slots)
                continue
            wave.append((index, row))
            if len(wave) == self._width:
                wave_number += 1
                self._run_wave(wave_number, wave_total, wave, slots)
                wave = []
        if wave:
            wave_number += 1
            self._run_wave(wave_number, wave_total, wave, slots)
        for slot in slots:
            if slot is None:
                raise VirusRedteamingError("a row was not processed")
        self._flush(slots)

    def _flush(self, slots: list[RedTeamResult | None]) -> None:
        ready = tuple(slot for slot in slots if slot is not None)
        self._writer.write(ready)
        destination = getattr(self._writer, "path", None)
        where = f" to {destination}" if destination else ""
        self._log.line(f"claude-red-team: wrote {len(ready)} rows{where}")

    def _run_wave(
        self,
        number: int,
        total: int,
        wave: list[tuple[int, RedTeamRow]],
        slots: list[RedTeamResult | None],
    ) -> None:
        ready: dict[str, Path | None] = {}
        for _, row in wave:
            if row.accession not in ready:
                ready[row.accession] = self._fasta.prepare(row.accession)
        self._log.line(
            f"wave {number}/{total}: {len(wave)} chains, "
            f"{len(ready)} sequence files"
        )
        runnable = [
            (index, row) for index, row in wave if ready[row.accession] is not None
        ]
        for accession, path in ready.items():
            if path is None:
                self._log.line(
                    f"wave {number}: {accession}: no FASTA, Claude not called"
                )
            else:
                self._log.line(f"wave {number}: {accession}: wrote {path}")
        for index, row in wave:
            if ready[row.accession] is None:
                slots[index] = _result(row, "no sequence", "")
        if not runnable:
            self._log.line(f"wave {number}/{total}: finished")
            self._flush(slots)
            return
        self._log.line(
            f"wave {number}/{total}: starting {len(runnable)} parallel chains"
        )
        with ThreadPoolExecutor(max_workers=self._width) as pool:
            finished = pool.map(self._exchange_row, runnable)
            for index, result in finished:
                slots[index] = result
        self._log.line(f"wave {number}/{total}: finished")
        self._flush(slots)

    def _exchange_row(self, item: tuple[int, RedTeamRow]) -> tuple[int, RedTeamResult]:
        index, row = item
        return index, self._exchange.run(row)
