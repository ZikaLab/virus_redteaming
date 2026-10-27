"""Load ``.env`` and run either the live layer or the Haiku test batch.

With no arguments this selects ``HarnessLayer.LIVE``: twenty chains, model
taken from the environment (default ``claude-haiku-5-5``), same ping
prompt on every chain.

``test-batch`` selects ``HarnessLayer.TEST_PARALLEL`` through
``HaikuBatch``: twenty chains, model pinned to ``claude-haiku-5-5``, each
chain asked for ``pong`` and its own number. Unit tests of that layer
still use a fake client and do not go through this script.
"""

from __future__ import annotations

import re
import sys

from dotenv import load_dotenv

from virus_redteaming.claude_harness.anthropic_chat import AnthropicChat
from virus_redteaming.claude_harness.config import ClaudeApiConfig
from virus_redteaming.claude_harness.errors import MissingClaudeApiKeyError
from virus_redteaming.claude_harness.haiku_batch import HaikuBatch
from virus_redteaming.claude_harness.layers import HarnessLayer
from virus_redteaming.claude_harness.workflow import ClaudePing

_PROMPT = "Reply with the single word pong."
_SECRET = re.compile(r"sk-ant-[A-Za-z0-9_\-]+")


def main(argv: list[str] | None = None) -> int:
    """Return 0 after twenty replies, 2 when the key or usage is wrong, 1 on failure.

    ``argv`` defaults to ``sys.argv[1:]``. ``[]`` is the live layer.
    ``["test-batch"]`` is the Haiku batch. Anything else prints usage
    and returns 2.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args not in ([], ["test-batch"]):
        print("usage: python scripts/claude_ping.py [test-batch]", file=sys.stderr)
        return 2
    load_dotenv(override=True)
    try:
        config = ClaudeApiConfig.from_environment()
    except MissingClaudeApiKeyError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    try:
        if args == ["test-batch"]:
            replies = HaikuBatch(config).run()
        else:
            replies = ClaudePing(AnthropicChat(config)).run_layer(
                HarnessLayer.LIVE,
                (_PROMPT,) * HarnessLayer.LIVE.chain_count(),
            )
    except Exception as exc:
        text = _SECRET.sub("***", str(exc))
        print(text, file=sys.stderr)
        if "anthropic-workspace-id" in text:
            print(
                "Set ANTHROPIC_WORKSPACE_ID in .env to a wrkspc_ id "
                "from the Claude Console workspaces page.",
                file=sys.stderr,
            )
        return 1
    for index, reply in enumerate(replies, start=1):
        print(f"{index}. {reply}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
