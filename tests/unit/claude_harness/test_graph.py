"""The graph invoke carries a file id only when the caller sets one."""

import pytest

from virus_redteaming.claude_harness.errors import EmptyClaudeReplyError
from virus_redteaming.claude_harness.workflow import ClaudePing

pytest.importorskip("langgraph")


class _Chat:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls: list[tuple[str, str | None]] = []

    def complete(self, prompt: str, file_id: str | None = None) -> str:
        self.calls.append((prompt, file_id))
        return self.reply


def test_ping_invoke_omits_file_id() -> None:
    chat = _Chat("pong")
    reply = ClaudePing(chat).run("Reply with the single word pong.")
    assert reply == "pong"
    assert chat.calls == [("Reply with the single word pong.", None)]


def test_run_passes_file_id_into_the_node() -> None:
    chat = _Chat("2341")
    reply = ClaudePing(chat).run("count", file_id="file_1")
    assert reply == "2341"
    assert chat.calls == [("count", "file_1")]


def test_empty_reply_with_file_id_raises() -> None:
    with pytest.raises(EmptyClaudeReplyError):
        ClaudePing(_Chat("  ")).run("count", file_id="file_1")
