"""How many Claude chains a run is allowed to start.

The harness has three layers. The layer fixes the chain count. Callers do
not pass a worker count of their own.

TEST
    The unit-test layer. It runs exactly one chain, on the caller's thread.
    The chat client is a fake that implements ``ChatTurn``. This layer does
    not open a network connection. Use it for one prompt, a missing API key,
    or an empty reply.

TEST_PARALLEL
    The test-batch layer. It runs exactly twenty chains at the same time,
    one per worker in a thread pool. Unit tests inject a fake ``ChatTurn``
    and stay on the machine. The Haiku batch (``HaikuBatch``) injects
    ``AnthropicChat`` pinned to ``claude-haiku-5-5`` and is the run that
    calls the API at this width. Replies come back in prompt order.

LIVE
    The live layer. It also runs exactly twenty chains at the same time. The
    script ``scripts/claude_ping.py`` is the entry that selects this layer,
    and it injects ``AnthropicChat``, so each chain calls the Claude API.
    The twenty chains share one compiled graph and one client. Each invoke
    carries its own prompt and reply. Unit tests must not select this layer
    against the network; they may inject a fake only to check the count.
"""

from enum import Enum

_TEST_CHAINS = 1
_PARALLEL_CHAINS = 20


class HarnessLayer(Enum):
    """One of the three run layers: ``test``, ``test_parallel``, or ``live``."""

    TEST = "test"
    TEST_PARALLEL = "test_parallel"
    LIVE = "live"

    def chain_count(self) -> int:
        """Return the number of chains this layer starts together.

        ``TEST`` returns 1. ``TEST_PARALLEL`` and ``LIVE`` return 20.
        A run whose prompt list has a different length is rejected before
        any chain starts.
        """
        return _CHAIN_COUNTS[self]


_CHAIN_COUNTS: dict[HarnessLayer, int] = {
    HarnessLayer.TEST: _TEST_CHAINS,
    HarnessLayer.TEST_PARALLEL: _PARALLEL_CHAINS,
    HarnessLayer.LIVE: _PARALLEL_CHAINS,
}
