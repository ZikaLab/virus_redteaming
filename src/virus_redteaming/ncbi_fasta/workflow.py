"""Fetch each uncached accession and write its FASTA file."""

from pathlib import Path

from virus_redteaming.clinical_fasta.protocols import (
    FastaEncoder,
    FastaRecordSource,
    FastaSink,
)
from virus_redteaming.ncbi_fasta.models import FetchNcbiFastaReport
from virus_redteaming.ncbi_fasta.protocols import FastaCache, GenBankSource


class NcbiFastaDownload:
    """Coordinates the scan, the cache, and one fetch per missing accession."""

    def __init__(
        self,
        source: GenBankSource,
        cache: FastaCache,
        records: FastaRecordSource,
        encoder: FastaEncoder,
        sink: FastaSink,
    ) -> None:
        self._source = source
        self._cache = cache
        self._records = records
        self._encoder = encoder
        self._sink = sink

    def run(self) -> FetchNcbiFastaReport:
        """Write missing FASTA files and return the written and cached paths."""
        scan = self._source.read()
        written: list[Path] = []
        cached: list[Path] = []
        for code in scan.codes:
            hit = self._cache.cached(code)
            if hit is not None:
                cached.append(hit)
                continue
            record = self._records.fetch(code)
            written.append(self._sink.write(self._encoder.encode(code, record)))
        return FetchNcbiFastaReport(tuple(written), tuple(cached), scan.blank_rows)
