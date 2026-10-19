"""The command exits before a call when the key or the table is unusable."""

from pathlib import Path

import pytest

from virus_redteaming.claude_harness.config import ClaudeApiConfig


def test_missing_key_exits_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda override: False)
    from virus_redteaming.__main__ import main

    assert main(["claude-red-team"]) == 2
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err


def test_bad_table_exits_1(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setattr("dotenv.load_dotenv", lambda override: False)
    missing = tmp_path / "missing.csv"
    from virus_redteaming.__main__ import main

    assert (
        main(
            [
                "claude-red-team",
                "--csv",
                str(missing),
                "--fasta",
                str(tmp_path),
                "--out",
                str(tmp_path / "out.csv"),
            ]
        )
        == 1
    )


def test_command_assembles_one_graph(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pytest.importorskip("langgraph")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setattr("dotenv.load_dotenv", lambda override: False)
    table = tmp_path / "t.csv"
    table.write_text(
        "ICTV virus,NCBI accession,ICTV family,ICTV genus,"
        "Human pathogen hazard group,Schedule 5\n"
        ",,,,,\n",
        encoding="utf-8",
    )
    built: list[object] = []

    class _Chat:
        def __init__(
            self,
            config: ClaudeApiConfig,
            *,
            timeout: float,
            max_tokens: int,
        ) -> None:
            self.timeout = timeout
            self.max_tokens = max_tokens

        def complete(self, prompt: str, file_id: str | None = None) -> str:
            return "pong"

    def _factory(config: ClaudeApiConfig, *, timeout: float, max_tokens: int) -> _Chat:
        chat = _Chat(config, timeout=timeout, max_tokens=max_tokens)
        built.append(chat)
        return chat

    from virus_redteaming.claude_harness import workflow

    monkeypatch.setattr(
        "virus_redteaming.claude_harness.anthropic_chat.AnthropicChat",
        _factory,
    )
    monkeypatch.setattr(
        workflow.ClaudePing,
        "run_layer",
        lambda self, layer, prompts: (),
    )
    from virus_redteaming.__main__ import main

    assert (
        main(
            [
                "claude-red-team",
                "--csv",
                str(table),
                "--fasta",
                str(tmp_path),
                "--out",
                str(tmp_path / "out.csv"),
            ]
        )
        == 0
    )
    assert len(built) == 1
    chat = built[0]
    assert isinstance(chat, _Chat)
    assert chat.timeout == 180.0
    assert chat.max_tokens == 4096
