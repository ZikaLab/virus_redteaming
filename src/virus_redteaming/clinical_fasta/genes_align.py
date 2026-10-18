"""Copy chosen accessions onto genes.csv with an atomic replace."""

import csv
from pathlib import Path
from typing import IO

from virus_redteaming.clinical_fasta.atomic_replace import replace_text
from virus_redteaming.clinical_fasta.errors import NcbiInputError
from virus_redteaming.clinical_fasta.models import ChosenAccession


class AtomicGenesAligner:
    """Reads genes.csv and replaces it. It does not open the criteria file."""

    def __init__(self, destination: Path) -> None:
        self._destination = destination

    def write(self, chosen: tuple[ChosenAccession, ...]) -> Path:
        """Replace genes.csv and return its path."""
        if not self._destination.is_file():
            raise NcbiInputError(f"query file is missing: {self._destination}")
        with self._destination.open(encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            try:
                header = next(reader)
            except StopIteration as exc:
                raise NcbiInputError("query file is empty") from exc
            if "Virus" not in header:
                raise NcbiInputError("query file is missing a Virus column")
            rows = list(reader)
        virus_index = header.index("Virus")
        if "Accession" in header:
            accession_index = header.index("Accession")
            output_header = header
        else:
            accession_index = len(header)
            output_header = [*header, "Accession"]
        lookup = {item.query: item.accession for item in chosen}

        def write_rows(handle: IO[str]) -> None:
            writer = csv.writer(handle)
            writer.writerow(output_header)
            for row in rows:
                padded = [*row, *([""] * (len(header) - len(row)))]
                query = padded[virus_index].strip()
                accession = lookup.get(query, "")
                if "Accession" in header:
                    padded[accession_index] = accession
                    writer.writerow(padded)
                else:
                    writer.writerow([*padded, accession])

        return replace_text(self._destination, write_rows)
