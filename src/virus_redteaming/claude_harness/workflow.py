"""Run the one-node Claude ping on one chain or on a whole layer."""

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import cast

from virus_redteaming.claude_harness.errors import (
    ChainCountError,
    EmptyClaudeReplyError,
)
from virus_redteaming.claude_harness.graph import PingState, build_ping_graph
from virus_redteaming.claude_harness.layers import HarnessLayer
from virus_redteaming.claude_harness.protocols import ChatTurn


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

    def run(self, prompt: str) -> str:
        """Run one chain and return a non-empty reply.

        This is the only path ``HarnessLayer.TEST`` uses. The parallel
        layers call it once per prompt, each call on its own worker.
        Every call invokes the compiled graph with a fresh state, so
        chains do not share a reply.
        """
        result = cast(PingState, self._app.invoke({"prompt": prompt, "reply": ""}))
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
