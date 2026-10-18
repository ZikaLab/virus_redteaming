"""Replace a destination only after the temporary file is complete."""

import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import IO

from virus_redteaming.clinical_fasta.errors import FastaWriteError


def replace_text(destination: Path, write_rows: Callable[[IO[str]], None]) -> Path:
    """Write through a temp file in the destination directory, then replace once."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        write_rows(handle)
        handle.flush()
        handle.close()
        os.replace(temporary, destination)
    except Exception as exc:
        handle.close()
        temporary.unlink(missing_ok=True)
        raise FastaWriteError(f"{destination.name} was not replaced") from exc
    return destination
