"""The wall-clock deadline raises. A completed inner timeout is left alone."""

import time

import pytest

from virus_redteaming.claude_harness.timed_chat import TimedChat


class _Slow:
    def complete(self, prompt: str, file_id: str | None = None) -> str:
        time.sleep(0.2)
        return "late"


class _InnerTimeout:
    def complete(self, prompt: str, file_id: str | None = None) -> str:
        raise TimeoutError("client")


def test_wall_clock_timeout_raises() -> None:
    with pytest.raises(TimeoutError, match="3 minutes"):
        TimedChat(_Slow(), seconds=0.05).complete("count", file_id="file_1")


def test_inner_timeout_is_reraised() -> None:
    with pytest.raises(TimeoutError, match="client"):
        TimedChat(_InnerTimeout(), seconds=1.0).complete("count")
