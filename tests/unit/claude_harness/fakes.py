"""Fakes for the red-team unit tests. They do not call Claude."""

from pathlib import Path

from virus_redteaming.claude_harness.models import RedTeamResult, RedTeamRow


class ScriptedChat:
    def __init__(self, replies: list[object]) -> None:
        self._replies = list(replies)
        self.calls: list[tuple[str, str | None]] = []

    def complete(self, prompt: str, file_id: str | None = None) -> str:
        self.calls.append((prompt, file_id))
        if not self._replies:
            raise AssertionError(prompt)
        item = self._replies.pop(0)
        if isinstance(item, Exception):
            raise item
        if not isinstance(item, str):
            raise AssertionError(item)
        return item


class RecordingStore:
    def __init__(self, directory: Path, fail: Exception | None = None) -> None:
        self.directory = directory
        self.fail = fail
        self.uploads: list[str] = []
        self.deletes: list[str] = []
        self.bodies: list[bytes] = []

    def upload(self, accession: str) -> str:
        if self.fail is not None:
            raise self.fail
        self.bodies.append((self.directory / f"{accession}.tmp").read_bytes())
        self.uploads.append(accession)
        return f"file_{accession}"

    def delete(self, file_id: str) -> None:
        self.deletes.append(file_id)


class MemoryWriter:
    def __init__(self) -> None:
        self.rows: tuple[RedTeamResult, ...] | None = None

    def write(self, rows: tuple[RedTeamResult, ...]) -> None:
        self.rows = rows


def row(
    virus: str = "virus",
    accession: str = "V00603",
    family: str = "Fam",
    genus: str = "Gen",
    hazard: str = "3",
    schedule: str = "0",
) -> RedTeamRow:
    return RedTeamRow(
        virus=virus,
        family=family,
        genus=genus,
        hazard_group=hazard,
        schedule_5=schedule,
        accession=accession,
    )
