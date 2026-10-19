"""One live Files API call. Skipped unless CLAUDE_LIVE_TEST=1."""

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.network

_LIVE = os.environ.get("CLAUDE_LIVE_TEST") == "1"
_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()


@pytest.mark.skipif(
    not _LIVE or not _KEY,
    reason="set CLAUDE_LIVE_TEST=1 and ANTHROPIC_API_KEY",
)
def test_one_short_sequence_returns_a_count(tmp_path: Path) -> None:
    from dotenv import load_dotenv

    from virus_redteaming.claude_harness.anthropic_chat import AnthropicChat
    from virus_redteaming.claude_harness.config import ClaudeApiConfig
    from virus_redteaming.claude_harness.models import RedTeamRow
    from virus_redteaming.claude_harness.prompt import SequencePrompt
    from virus_redteaming.claude_harness.sequence import FastaSequence
    from virus_redteaming.claude_harness.timed_chat import TimedChat
    from virus_redteaming.claude_harness.upload import SequenceUpload
    from virus_redteaming.claude_harness.workflow import ClaudePing, RedTeamExchange

    load_dotenv(override=True)
    fasta = tmp_path / "V00603.fasta"
    fasta.write_text(">fixture\nACGTACGTACGT\n", encoding="utf-8")

    prepared = FastaSequence(tmp_path).prepare("V00603")
    assert prepared is not None
    config = ClaudeApiConfig.from_environment()
    chat = AnthropicChat(config, timeout=180.0, max_tokens=4096)
    store = SequenceUpload(config, tmp_path)
    result = RedTeamExchange(
        ClaudePing(TimedChat(chat)),
        store,
        SequencePrompt(),
        tmp_path,
    ).run(
        RedTeamRow(
            virus="fixture",
            family="",
            genus="",
            hazard_group="",
            schedule_5="",
            accession="V00603",
        )
    )
    assert result.claude_response.strip() != ""
    assert result.claude_response != "no sequence"
