"""The ping reads the key name and returns a fake reply without the network."""

import threading

import pytest

from virus_redteaming.claude_harness.config import ClaudeApiConfig
from virus_redteaming.claude_harness.errors import (
    ChainCountError,
    EmptyClaudeReplyError,
    MissingClaudeApiKeyError,
)
from virus_redteaming.claude_harness.layers import HarnessLayer
from virus_redteaming.claude_harness.workflow import ClaudePing

pytest.importorskip("langgraph")


class _FakeChat:
    def __init__(self, reply: str) -> None:
        self._reply = reply
        self.prompts: list[str] = []

    def complete(self, prompt: str, file_id: str | None = None) -> str:
        self.prompts.append(prompt)
        return self._reply


def test_missing_key_names_the_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(MissingClaudeApiKeyError, match="ANTHROPIC_API_KEY"):
        ClaudeApiConfig.from_environment()


def test_blank_key_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
    with pytest.raises(MissingClaudeApiKeyError):
        ClaudeApiConfig.from_environment()


def test_repr_omits_the_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-secret")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-haiku-5-5")
    config = ClaudeApiConfig.from_environment()
    assert config.api_key == "sk-ant-test-secret"
    assert "sk-ant-test-secret" not in repr(config)
    assert config.model == "claude-haiku-5-5"


def test_workspace_id_is_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-secret")
    monkeypatch.delenv("ANTHROPIC_WORKSPACE_ID", raising=False)
    config = ClaudeApiConfig.from_environment()
    assert config.workspace_id is None


def test_workspace_id_is_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-secret")
    monkeypatch.setenv("ANTHROPIC_WORKSPACE_ID", " wrkspc_example ")
    config = ClaudeApiConfig.from_environment()
    assert config.workspace_id == "wrkspc_example"


def test_default_model_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-secret")
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    config = ClaudeApiConfig.from_environment()
    assert config.model == "claude-haiku-5-5"


def test_graph_returns_the_fake_reply() -> None:
    chat = _FakeChat("pong")
    reply = ClaudePing(chat).run("Reply with the single word pong.")
    assert reply == "pong"
    assert chat.prompts == ["Reply with the single word pong."]


def test_empty_reply_is_an_error() -> None:
    with pytest.raises(EmptyClaudeReplyError):
        ClaudePing(_FakeChat("  ")).run("ping")


def test_test_layer_runs_one_chain() -> None:
    chat = _FakeChat("pong")
    replies = ClaudePing(chat).run_layer(HarnessLayer.TEST, ("only",))
    assert HarnessLayer.TEST.chain_count() == 1
    assert replies == ("pong",)
    assert chat.prompts == ["only"]


def test_test_layer_rejects_twenty_prompts() -> None:
    prompts = tuple(f"chain-{index}" for index in range(20))
    with pytest.raises(ChainCountError, match="test runs 1 chain"):
        ClaudePing(_FakeChat("pong")).run_layer(HarnessLayer.TEST, prompts)


def test_parallel_layer_runs_twenty_chains() -> None:
    barrier = threading.Barrier(20)
    prompts = tuple(f"chain-{index}" for index in range(20))

    class _GatedChat:
        def complete(self, prompt: str, file_id: str | None = None) -> str:
            barrier.wait(timeout=5)
            return prompt

    replies = ClaudePing(_GatedChat()).run_layer(HarnessLayer.TEST_PARALLEL, prompts)
    assert HarnessLayer.TEST_PARALLEL.chain_count() == 20
    assert replies == prompts


def test_parallel_layer_rejects_one_prompt() -> None:
    with pytest.raises(ChainCountError, match="test_parallel runs 20 chains"):
        ClaudePing(_FakeChat("pong")).run_layer(HarnessLayer.TEST_PARALLEL, ("only",))


def test_live_layer_runs_twenty_chains_on_the_injected_client() -> None:
    barrier = threading.Barrier(20)
    prompts = tuple(f"live-{index}" for index in range(20))

    class _GatedChat:
        def complete(self, prompt: str, file_id: str | None = None) -> str:
            barrier.wait(timeout=5)
            return prompt

    replies = ClaudePing(_GatedChat()).run_layer(HarnessLayer.LIVE, prompts)
    assert HarnessLayer.LIVE.chain_count() == 20
    assert replies == prompts


def test_haiku_batch_pins_model_and_builds_twenty_prompts() -> None:
    pytest.importorskip("langchain_anthropic")
    from virus_redteaming.claude_harness.haiku_batch import (
        HAIKU_MODEL,
        haiku_batch_config,
        haiku_batch_prompts,
    )

    config = ClaudeApiConfig(
        api_key="sk-ant-test-secret",
        model="claude-opus-5-5",
        workspace_id="wrkspc_example",
    )
    pinned = haiku_batch_config(config)
    prompts = haiku_batch_prompts()
    assert pinned.model == HAIKU_MODEL
    assert pinned.model == "claude-haiku-5-5"
    assert pinned.workspace_id == "wrkspc_example"
    assert pinned.api_key == "sk-ant-test-secret"
    assert "sk-ant-test-secret" not in repr(pinned)
    assert len(prompts) == HarnessLayer.TEST_PARALLEL.chain_count()
    assert prompts[0].endswith("1.")
    assert prompts[-1].endswith("20.")


def test_live_layer_rejects_one_prompt() -> None:
    with pytest.raises(ChainCountError, match="live runs 20 chains"):
        ClaudePing(_FakeChat("pong")).run_layer(HarnessLayer.LIVE, ("only",))
