"""Test-batch mode: twenty parallel chains pinned to Claude Haiku.

``HarnessLayer.TEST_PARALLEL`` owns the width: twenty chains, one thread
each. Unit tests of that layer inject a fake ``ChatTurn`` and stay
offline. This module is the run that uses the same width against the
API.

The model is always ``claude-haiku-5-5``. ``ANTHROPIC_MODEL`` is
ignored so a shell or ``.env`` override cannot send the batch to
another model. The API key and workspace id still come from
``ClaudeApiConfig``. The twenty chains share one ``AnthropicChat`` and
one compiled graph. Each chain gets its own prompt, numbered from 1
to 20, and the replies come back in that order.

Run it with ``python scripts/claude_ping.py test-batch``.
"""

from virus_redteaming.claude_harness.anthropic_chat import AnthropicChat
from virus_redteaming.claude_harness.config import ClaudeApiConfig
from virus_redteaming.claude_harness.layers import HarnessLayer
from virus_redteaming.claude_harness.workflow import ClaudePing

HAIKU_MODEL = "claude-haiku-5-5"


def haiku_batch_config(config: ClaudeApiConfig) -> ClaudeApiConfig:
    """Copy ``config`` with the model pinned to Claude Haiku.

    The key and workspace id are unchanged. The model is
    ``claude-haiku-5-5`` even when ``config.model`` names something else.
    """
    return ClaudeApiConfig(
        api_key=config.api_key,
        model=HAIKU_MODEL,
        workspace_id=config.workspace_id,
    )


def haiku_batch_prompts() -> tuple[str, ...]:
    """Return one prompt per ``TEST_PARALLEL`` chain, numbered from 1.

    Chain ``n`` is asked for the single word ``pong`` and the number
    ``n``. Twenty prompts is the whole batch. The numbers make each reply
    traceable to its chain.
    """
    count = HarnessLayer.TEST_PARALLEL.chain_count()
    return tuple(
        f"Reply with the single word pong and the number {index}."
        for index in range(1, count + 1)
    )


class HaikuBatch:
    """Run the twenty-chain test batch on Claude Haiku.

    Construct it with the environment config. ``run`` pins the model,
    builds one ``AnthropicChat``, and calls ``ClaudePing.run_layer``
    with ``HarnessLayer.TEST_PARALLEL``. That layer starts all twenty
    chains together. A missing key is the caller's problem: this class
    does not read the environment.
    """

    def __init__(self, config: ClaudeApiConfig) -> None:
        pinned = haiku_batch_config(config)
        self._ping = ClaudePing(AnthropicChat(pinned))

    def run(self) -> tuple[str, ...]:
        """Send the twenty numbered prompts and return the twenty replies."""
        return self._ping.run_layer(HarnessLayer.TEST_PARALLEL, haiku_batch_prompts())
