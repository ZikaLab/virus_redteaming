"""Progress for a live red-team run, on the terminal and in a log file."""

import sys
import threading
from pathlib import Path
from typing import TextIO


class StdoutLog:
    """Print one progress entry and append the same text to a log file."""

    def __init__(self, stream: TextIO | None = None, path: Path | None = None) -> None:
        self._stream = sys.stdout if stream is None else stream
        self._path = path
        self._lock = threading.Lock()
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")

    def line(self, text: str) -> None:
        """Write ``text`` and flush it."""
        with self._lock:
            print(text, file=self._stream, flush=True)
            if self._path is not None:
                with self._path.open("a", encoding="utf-8") as handle:
                    handle.write(text)
                    handle.write("\n")
                    handle.flush()
