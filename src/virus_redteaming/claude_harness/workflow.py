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
from virus_redteaming.claude_harness.protocols import ChatTurn, SequenceStore
from virus_redteaming.claude_harness.sequence import FastaSequence
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


class RedTeamExchange:
    """One accession: upload, count, then secondary structure."""

    def __init__(
        self,
        ping: ClaudePing,
        store: SequenceStore,
        prompts: SequencePrompt,
        directory: Path,
    ) -> None:
        self._ping = ping
        self._store = store
        self._prompts = prompts
        self._directory = directory

    def run(self, row: RedTeamRow) -> RedTeamResult:
        """Send both prompts for ``row`` and delete the remote file."""
        file_id: str | None = None
        hidden = (str(self._directory / f"{row.accession}.tmp"),)
        try:
            try:
                file_id = self._store.upload(row.accession)
            except Exception as exc:
                return _result(row, redact_client_error(exc, hidden), "")
            try:
                count = self._ping.run(self._prompts.count(), file_id=file_id)
            except (EmptyClaudeReplyError, TimeoutError):
                return _result(row, "no response", "")
            except Exception as exc:
                return _result(row, redact_client_error(exc, hidden), "")
            response = _count_cell(count)
            try:
                structure = self._ping.run(self._prompts.structure(), file_id=file_id)
            except (EmptyClaudeReplyError, TimeoutError):
                return _result(row, response, "no response")
            except Exception as exc:
                return _result(row, response, redact_client_error(exc, hidden))
            return _result(row, response, structure)
        finally:
            if file_id is not None:
                try:
                    self._store.delete(file_id)
                except Exception:
                    pass


class RedTeamBatch:
    """Run accession chains in waves. ``run_layer`` is not used."""

    def __init__(
        self,
        source: MergedRedTeamSource,
        fasta: FastaSequence,
        exchange: RedTeamExchange,
        writer: RedTeamReportWriter,
        width: int,
    ) -> None:
        self._source = source
        self._fasta = fasta
        self._exchange = exchange
        self._writer = writer
        self._width = width

    def run(self) -> None:
        """Read the table, run every wave, and replace the output CSV."""
        rows = self._source.read()
        slots: list[RedTeamResult | None] = [None] * len(rows)
        wave: list[tuple[int, RedTeamRow]] = []
        for index, row in enumerate(rows):
            if row.accession == "":
                slots[index] = _result(row, "no sequence", "")
                continue
            wave.append((index, row))
            if len(wave) == self._width:
                self._run_wave(wave, slots)
                wave = []
        if wave:
            self._run_wave(wave, slots)
        results: list[RedTeamResult] = []
        for slot in slots:
            if slot is None:
                raise VirusRedteamingError("a row was not processed")
            results.append(slot)
        self._writer.write(tuple(results))

    def _run_wave(
        self,
        wave: list[tuple[int, RedTeamRow]],
        slots: list[RedTeamResult | None],
    ) -> None:
        ready: dict[str, Path | None] = {}
        for _, row in wave:
            if row.accession not in ready:
                ready[row.accession] = self._fasta.prepare(row.accession)
        runnable = [
            (index, row) for index, row in wave if ready[row.accession] is not None
        ]
        for index, row in wave:
            if ready[row.accession] is None:
                slots[index] = _result(row, "no sequence", "")
        if not runnable:
            return
        with ThreadPoolExecutor(max_workers=self._width) as pool:
            finished = pool.map(self._exchange_row, runnable)
            for index, result in finished:
                slots[index] = result

    def _exchange_row(self, item: tuple[int, RedTeamRow]) -> tuple[int, RedTeamResult]:
        index, row = item
        return index, self._exchange.run(row)
