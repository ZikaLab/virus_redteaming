"""Load schedule-5 names from a markdown bullet list."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class Schedule5NameSource(Protocol):
    def load(self, path: Path) -> tuple[str, ...]:
        """Return schedule-5 names in file order."""


class MarkdownBulletNameSource:
    def load(self, path: Path) -> tuple[str, ...]:
        names: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("- "):
                names.append(line[2:].strip())
        return tuple(names)
