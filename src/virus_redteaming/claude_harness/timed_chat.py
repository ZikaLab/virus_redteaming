"""Stop one Claude call when three minutes have passed."""

from concurrent.futures import ThreadPoolExecutor

from virus_redteaming.claude_harness.protocols import ChatTurn


class TimedChat:
    """``ChatTurn`` that gives the inner client a wall-clock deadline."""

    def __init__(self, chat: ChatTurn, seconds: float = 180.0) -> None:
        self._chat = chat
        self._seconds = seconds

    def complete(self, prompt: str, file_id: str | None = None) -> str:
        """Return the inner reply, or raise ``TimeoutError`` at the deadline."""
        pool = ThreadPoolExecutor(max_workers=1)
        future = pool.submit(self._chat.complete, prompt, file_id)
        try:
            return future.result(timeout=self._seconds)
        except TimeoutError as exc:
            if future.done():
                raise
            raise TimeoutError("Claude did not reply within 3 minutes") from exc
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
