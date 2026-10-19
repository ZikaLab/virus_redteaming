"""One chain uploads once, asks twice, and deletes the remote file."""

from pathlib import Path

from tests.unit.claude_harness.fakes import RecordingStore, ScriptedChat, row
from virus_redteaming.claude_harness.errors import EmptyClaudeReplyError
from virus_redteaming.claude_harness.prompt import SequencePrompt
from virus_redteaming.claude_harness.workflow import ClaudePing, RedTeamExchange


def _exchange(
    tmp_path: Path,
    chat: ScriptedChat,
    store: RecordingStore | None = None,
) -> tuple[RedTeamExchange, RecordingStore]:
    body = tmp_path / "V00603.tmp"
    body.write_bytes(b"ACGT ACGT\nTTTT\n")
    used = store if store is not None else RecordingStore(tmp_path)
    exchange = RedTeamExchange(
        ClaudePing(chat),
        used,
        SequencePrompt(),
        tmp_path,
    )
    return exchange, used


def test_second_call_reuses_the_same_file_id(tmp_path: Path) -> None:
    chat = ScriptedChat(["2341", "((((....))))"])
    exchange, store = _exchange(tmp_path, chat)
    result = exchange.run(row())
    assert store.uploads == ["V00603"]
    assert chat.calls[0][1] == chat.calls[1][1] == "file_V00603"
    assert result.claude_response == "2341"
    assert result.secondary_structure == "((((....))))"
    assert store.deletes == ["file_V00603"]


def test_count_reply_stores_a_number_or_the_first_line(tmp_path: Path) -> None:
    integer = ScriptedChat(["2341\n", "dot"])
    exchange, _store = _exchange(tmp_path, integer)
    assert exchange.run(row()).claude_response == "2341"
    prose = ScriptedChat(["\nabout 2341 bases\nmore\n", "dot"])
    exchange, _store = _exchange(tmp_path, prose)
    assert exchange.run(row()).claude_response == "about 2341 bases"


def test_upload_reads_the_tmp_for_the_accession(tmp_path: Path) -> None:
    chat = ScriptedChat(["10", "dot"])
    exchange, store = _exchange(tmp_path, chat)
    exchange.run(row())
    assert store.bodies == [b"ACGT ACGT\nTTTT\n"]


def test_uploaded_file_is_deleted_when_the_second_call_is_skipped(
    tmp_path: Path,
) -> None:
    chat = ScriptedChat([EmptyClaudeReplyError("empty")])
    exchange, store = _exchange(tmp_path, chat)
    result = exchange.run(row())
    assert result.claude_response == "no response"
    assert result.secondary_structure == ""
    assert store.deletes == ["file_V00603"]
    assert len(chat.calls) == 1


def test_timeout_or_empty_reply_does_not_ask_for_structure(tmp_path: Path) -> None:
    chat = ScriptedChat([TimeoutError("stuck")])
    exchange, _store = _exchange(tmp_path, chat)
    result = exchange.run(row())
    assert result.claude_response == "no response"
    assert result.secondary_structure == ""
    assert len(chat.calls) == 1


def test_model_text_no_response_still_asks_for_structure(tmp_path: Path) -> None:
    chat = ScriptedChat(["no response", "((((....))))"])
    exchange, _store = _exchange(tmp_path, chat)
    result = exchange.run(row())
    assert result.claude_response == "no response"
    assert result.secondary_structure == "((((....))))"


def test_non_empty_count_then_structure_is_stored(tmp_path: Path) -> None:
    chat = ScriptedChat(["about 2341 bases", "((((....))))\n...."])
    exchange, _store = _exchange(tmp_path, chat)
    result = exchange.run(row())
    assert result.claude_response == "about 2341 bases"
    assert result.secondary_structure == "((((....))))\n...."


def test_structure_timeout_stores_no_response(tmp_path: Path) -> None:
    chat = ScriptedChat(["2341", TimeoutError("stuck")])
    exchange, store = _exchange(tmp_path, chat)
    result = exchange.run(row())
    assert result.claude_response == "2341"
    assert result.secondary_structure == "no response"
    assert store.deletes == ["file_V00603"]


def test_api_key_is_redacted(tmp_path: Path) -> None:
    secret = "sk-ant-abc_DEF-123"
    chat = ScriptedChat([RuntimeError(f"bad key {secret} {tmp_path / 'V00603.tmp'}")])
    exchange, store = _exchange(tmp_path, chat)
    result = exchange.run(row())
    assert secret not in result.claude_response
    assert "***" in result.claude_response
    assert str(tmp_path / "V00603.tmp") not in result.claude_response
    assert store.deletes == ["file_V00603"]
