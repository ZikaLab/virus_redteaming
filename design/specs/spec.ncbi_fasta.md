# spec.ncbi_fasta.md

**Status:** accepted  
**Build:** [build.ncbi_fasta.md](build.ncbi_fasta.md)

## Goal

One command reads `GenBank accessions` from a merged virus table and writes one nucleotide FASTA file per distinct accession under `output/NCBI_fasta`.

The CSV path is a command argument. The default path is `output/HSE-virus_Cat1-virus_merged.csv`.

A blank `GenBank accessions` cell is skipped. Each parsed accession is fetched from nuccore.

## Constitution

Layout follows `constitution/CONSTITUTION.md`. The package is `src/virus_redteaming/ncbi_fasta/`. `src/virus_redteaming/__main__.py` only assembles the object graph.

## Data profile

`output/HSE-virus_Cat1-virus_merged.csv` at the time of this spec:

| Measure | Count |
| --- | --- |
| Data rows | 424 |
| Blank `GenBank accessions` | 33 |
| Populated `GenBank accessions` | 391 |
| Accession occurrences | 771 |
| Distinct accession codes | 727 |

NCBI `nuccore` esummary resolves every one of the 727 codes to the same stem. No summary record has a `replacedby` value. The `status` field is empty on all 727. The version suffix on `accessionversion` is:

| Version | Codes |
| --- | --- |
| `.1` | 656 |
| `.2` | 64 |
| `.3` | 5, including `MN908947.3` |
| `.4` | 1, `AY632536.4` |
| `.5` | 1, `AF291704.5` |

None of the 727 cells stores that version. `efetch` FASTA for `V00603` begins `>V00603.1`. `efetch` FASTA for `J02151` begins `>J02151.1`. The accession is the first header token.

On every row of this file, splitting the cell on `;` and `:` yields the same codes as `GenBankAccessionParser.codes`, and those codes joined with `; ` equal the `NCBI accession` cell.

## Segment grammar

Read `GenBank accessions`. Replace U+00A0 with a space and strip both ends.

1. An empty cell is a blank row. Increment the blank-row count and take no code.
2. Split a populated cell on `;`. Strip each piece. A terminal `;` leaves an empty piece; drop that piece. An empty piece between two segments is `NcbiFastaInputError`.
3. For each segment, split on the first `:`.
   - Text before `:` is the segment label (`RNA1`, `L`, `Seg1`, `DNA-C`). An empty label is `NcbiFastaInputError`.
   - Text after `:` is the accession text.
   - A segment with no `:` is itself the accession text.
4. Remove one trailing coordinate range, `\(\d+\.\d+\)`, and the whitespace around it.
5. The remaining text must match the accession pattern in `GenBankAccessionParser`:

```text
^(?:[A-Z]{2}_\d{6,9}|[A-Z]{2}\d{8}|[A-Z]{2}\d{6}|[A-Z]\d{5})(?:\.\d+)?$
```

Every code that pattern accepts also matches `AccessionIdentity`'s token pattern, including a version NCBI adds later (`V00603` against `V00603.1`, `AF291704` against `AF291704.5`). The merged table contains no 4- to 6-letter WGS or TSA accessions, so this command does not widen the pattern to accept them.

A populated cell that fails this grammar raises `NcbiFastaInputError` before any Entrez call. Examples: `No entry in Genbank`, `RNA1: ???`, `: V00603`, `L: V00603; ; S: J02151`.

| Cell | Result |
| --- | --- |
| empty or whitespace | Blank row |
| `U87411` | `U87411` |
| `RNA1: V00603; RNA2: J02151` | `V00603`, then `J02151` |
| `L: AY358022; S: AY358023` | `AY358022`, then `AY358023` |
| `Seg1: AF133428; Seg2: AF139758` | `AF133428`, then `AF139758` |
| `DNA-C: EF546812; DNA-M: EF546811` | `EF546812`, then `EF546811` |
| `Seg1: AH009795(1.3949); Seg4: AF403390` | `AH009795`, then `AF403390` |
| `AF052015; AF052015` | `AF052015` once |

`GenBankSegmentParser` is the parser this command runs. The offline test checks that its `codes` equal `GenBankAccessionParser.codes` for every cell in the merged file.

## Which codes are fetched

Walk rows from top to bottom. Inside a row, keep segment order. Across the file, keep each code once, at its first appearance. A later row that repeats `V00603` does not schedule another download.

There are 727 distinct codes in the current table. Calls are serial. `Bio.Entrez` applies its own rate limit, 3 requests per second without an API key and 10 with one.

Sequence length is not a filter. NCBI reports `V00603.1` at 2341 bp and `K00423.1` at 1882 bp. Those records are written.

## Resume and cache validation

`NcbiFastaDownload` does not read the filesystem directly. It queries an injected `FastaCache` (`cached(accession: str) -> Path | None`) before calling `FastaRecordSource.fetch`.

`DirectoryFastaCache` checks `{out}/{accession}.fasta`:

| Existing file state | Action |
| --- | --- |
| Regular UTF-8 file that `Bio.SeqIO.parse` parses as one FASTA record with a non-empty sequence and a header accepted by `AccessionIdentity.matches(record, accession)` | Cache hit. Return the path. Do not call Entrez. |
| Missing, empty, unreadable, zero or multiple FASTA records, empty sequence, or a header that fails `AccessionIdentity` | Cache miss. Return `None`. |

A cache hit matches the requested stem. The cells in this table have no version, so a file whose header is `>AF291704.1` is a hit for `AF291704` even when NCBI's current record is `AF291704.5`. Deleting that file is what causes the next run to fetch the current record.

A cache miss leaves the existing file in place until fetch, encode, and atomic replace all succeed. A fetch or identity failure raises, and that file is still there for the next run.

`AtomicPathFastaSink` writes a temporary file in the output directory and replaces the destination with `os.replace`. A failed replace deletes the temporary file and leaves that destination as it was. Files already replaced in the run stay on disk, so the next run continues at the first code that is not a cache hit.

## Download

Inject the existing FASTA stack:

| Type | Role |
| --- | --- |
| `NcbiEntrezConfig` | Email, optional API key, `tool="virus_redteaming_ncbi_fasta"`. |
| `BiopythonEntrezClient.fetch_fasta` | One `efetch` per uncached code: `db="nuccore"`, `rettype="fasta"`, `retmode="text"`. |
| `FastaFetchSource` with `AccessionIdentity` | One non-empty FASTA record whose header matches the requested code. |
| `BiopythonFastaEncoder` | FASTA text for that record. `FastaRecord.accession` is the requested code. |
| `AtomicPathFastaSink` | Writes `{out}/{accession}.fasta`. |

Construct `NcbiEntrezConfig` with `tool="virus_redteaming_ncbi_fasta"`. `NcbiEntrezConfig.from_environment` sets the tool name to `virus_redteaming_clinical_fasta`, so this command reads `NCBI_EMAIL` and the optional `NCBI_API_KEY` and passes them to the constructor with the tool name above. The key is omitted from the call when empty, and it stays out of logs, exception text, and `repr`.

`AccessionIdentity` is the header check. The requested stem equals the stem of `record.id`, of a `|` piece of `record.id`, or of `record.name`. A version on only one side still matches, which is the case for every code in this table: the cell has no version and the FASTA header does. When both sides have a version, the versions are equal.

Checked `efetch` headers put the versioned accession in the first token:

| Requested | First FASTA token | File name |
| --- | --- | --- |
| `V00603` | `V00603.1` | `V00603.fasta` |
| `J02151` | `J02151.1` | `J02151.fasta` |

`AccessionIdentity` also accepts a bar token such as `emb|V00603.1|` when a header contains one. These two `efetch` responses do not use that form. The same stem rule accepts the higher versions in the table, including `AF291704` against `AF291704.5` and `AY632536` against `AY632536.4`. The encoder writes the `SeqRecord` NCBI returned, so `V00603.fasta` begins `>V00603.1`.

A header stem other than the requested stem is `NcbiRecordRejected`. `V00603.1` requested against a header `V00603.2` is `NcbiRecordRejected`. The run stops on that error. Files already replaced stay on disk.

## Output directory

The default directory is `output/NCBI_fasta` at the repository root. The sink creates it when it is missing.

## CLI

```bash
python -m virus_redteaming fetch-ncbi-fasta --csv output/HSE-virus_Cat1-virus_merged.csv
```

| Argument | Rule |
| --- | --- |
| `--csv` | Merged table path. Default: `output/HSE-virus_Cat1-virus_merged.csv`. |
| `--out` | FASTA directory. Default: `output/NCBI_fasta`. |

Stdout prints each newly written path, one per line, then:

```text
skipped {blank_rows} blank rows
cached {cached_count} accessions
fetched {fetched_count} accessions
```

| Exit | Condition |
| --- | --- |
| 0 | The table was read and every distinct code is a written file or a cache hit. An all-blank table exits 0 with zero fetches. |
| 2 | `NCBI_EMAIL` is missing or contains whitespace (`NcbiConfigError`), checked when assembling the command. |
| 1 | `NcbiFastaInputError`, `NcbiFetchError`, `NcbiRecordRejected`, or `FastaWriteError`. |

## Types

Package: `src/virus_redteaming/ncbi_fasta/`.

| Type | Module | Responsibility |
| --- | --- | --- |
| `NcbiFastaInputError` | `errors.py` | Missing CSV, missing `GenBank accessions` header, or a populated cell that fails the segment grammar. Subclass of `VirusRedteamingError`. |
| `GenBankTableScan` | `models.py` | Frozen: `codes: tuple[str, ...]`, `blank_rows: int`. |
| `FetchNcbiFastaReport` | `models.py` | Frozen: `written: tuple[Path, ...]`, `cached: tuple[Path, ...]`, `blank_rows: int`. |
| `SegmentParser` | `protocols.py` | `codes(cell: str) -> tuple[str, ...]`. |
| `GenBankSource` | `protocols.py` | `read() -> GenBankTableScan`. |
| `FastaCache` | `protocols.py` | `cached(accession: str) -> Path | None`. |
| `entrez_config_from_environment` | `config.py` | Reads `NCBI_EMAIL` and optional `NCBI_API_KEY`, returning `NcbiEntrezConfig` with `tool="virus_redteaming_ncbi_fasta"`. |
| `GenBankSegmentParser` | `parse.py` | Segment grammar in this spec. |
| `MergedGenBankSource` | `source.py` | Reads the CSV and returns `GenBankTableScan`. |
| `DirectoryFastaCache` | `cache.py` | Validates `{out}/{accession}.fasta` as one non-empty FASTA record matching `AccessionIdentity`. |
| `NcbiFastaDownload` | `workflow.py` | Coordinates `GenBankSource`, `FastaCache`, `FastaRecordSource`, `FastaEncoder`, and `FastaSink`. |

`NcbiFastaDownload` depends only on Protocols (`GenBankSource`, `FastaCache`, `FastaRecordSource`, `FastaEncoder`, `FastaSink`). It does not touch the filesystem, does not import Biopython, and does not open a socket.

## Errors

| Condition | Type |
| --- | --- |
| CSV missing, not a regular file, or header lacks `GenBank accessions` | `NcbiFastaInputError` |
| Populated cell fails the segment grammar | `NcbiFastaInputError` |
| Email missing or containing whitespace | `NcbiConfigError` |
| Transport failure or a non-success Entrez response | `NcbiFetchError` |
| FASTA parse fails, record count is not one, header identity fails, or the sequence is empty | `NcbiRecordRejected` |
| Atomic replace fails | `FastaWriteError` |

## Tests

Unit tests live in `tests/unit/ncbi_fasta/`. They use Protocol fakes and do not call NCBI.

| Test | Asserts |
| --- | --- |
| `test_labelled_segments_keep_the_code_after_each_colon` | `RNA1: V00603; RNA2: J02151` yields `V00603`, then `J02151`. |
| `test_bare_accession_is_kept` | `U87411` yields `U87411`. |
| `test_coordinate_suffix_is_stripped_after_colon` | `Seg1: AH009795(1.3949); Seg4: AF403390` yields `AH009795`, then `AF403390`. |
| `test_wgs_accession_is_rejected` | `CASDWV010000980` raises `NcbiFastaInputError`. |
| `test_repeated_code_inside_one_cell_is_kept_once` | `AF052015; AF052015` yields `AF052015`. |
| `test_blank_and_nbsp_cells_are_empty_or_stripped` | Whitespace and a U+00A0-only cell return no codes. U+00A0 around a code is stripped. |
| `test_other_segment_labels_keep_the_code` | `L:`, `S:`, `Seg1:`, `DNA-C:`, and `DNA-M:` labels keep their codes. |
| `test_malformed_populated_cell_raises_input_error` | `;`, `No entry in Genbank`, `RNA1: ???`, `: V00603`, and `L: V00603; ; S: J02151` raise `NcbiFastaInputError`. |
| `test_blank_genbank_cell_is_skipped` | A blank cell between two coded cells adds those two codes and `blank_rows == 1`. |
| `test_repeated_accession_across_rows_is_scheduled_once` | Two rows containing `V00603` produce one scheduled code. |
| `test_missing_file_raises_input_error` | Missing CSV path raises `NcbiFastaInputError`. |
| `test_directory_path_raises_input_error` | A directory path raises `NcbiFastaInputError`. |
| `test_short_row_and_nbsp_blank_are_skipped` | A short row and a U+00A0-only cell increment `blank_rows`. |
| `test_missing_file_returns_none` | A missing `.fasta` file returns `None` from `DirectoryFastaCache`. |
| `test_valid_single_record_is_a_hit` | A valid single-record FASTA matching `AccessionIdentity` returns its path from `DirectoryFastaCache`. |
| `test_valid_cached_fasta_file_is_a_cache_hit` | A file containing `>V00603.1\nACGT\n` for `V00603` is a cache hit and `fetch` is not called. |
| `test_header_only_or_mismatched_cached_file_is_refetched` | A file containing only `>V00603.1\n` (empty sequence) or `>U87411.1\nACGT\n` (wrong stem) is a cache miss and is re-fetched and replaced. |
| `test_empty_or_non_fasta_file_returns_none` | An empty file or plain text without `>` returns `None` from `DirectoryFastaCache`. |
| `test_multiple_records_return_none` | A multi-record FASTA file returns `None` from `DirectoryFastaCache`. |
| `test_unreadable_utf8_bytes_return_none` | Invalid UTF-8 bytes in `{out}/{accession}.fasta` return `None` from `DirectoryFastaCache`. |
| `test_versioned_header_matches_unversioned_request` | Requested `V00603` matches FASTA id `V00603.1`. Requested `AF291704` matches FASTA id `AF291704.5`. A bar token `emb\|V00603.1\|` also matches `V00603`. The written path for `V00603` ends with `V00603.fasta`. |
| `test_older_cached_version_is_a_hit` | A file `>AF291704.1\nACGT\n` is a cache hit for `AF291704`. |
| `test_different_header_stem_is_rejected` | Requested `V00603` with FASTA id `NC_002023.1` raises `NcbiRecordRejected` and writes no file for that code. |
| `test_conflicting_versions_are_rejected` | Requested `V00603.1` with FASTA id `V00603.2` raises `NcbiRecordRejected`. |
| `test_short_sequence_is_written` | A 2341 bp record is written. |
| `test_missing_genbank_header_raises_input_error` | A CSV without `GenBank accessions` raises `NcbiFastaInputError` and does not fetch. |
| `test_interrupted_run_resumes_without_refetching_earlier_files` | When the second accession fails, the first written FASTA file stays on disk and is cached on the next run without a second `fetch_fasta` call. |
| `test_protocol_fakes_skip_cached_codes_and_stop_on_fetch_error` | A cache hit is not fetched. A later fetch error is not encoded or written, and the run stops. |
| `test_missing_email_exits_2` | Missing `NCBI_EMAIL` exits `2`. |
| `test_whitespace_email_exits_2` | `NCBI_EMAIL` containing whitespace exits `2`. |
| `test_bad_table_exits_1` | Missing `GenBank accessions` header exits `1`. |
| `test_fetch_and_write_errors_exit_1` | `NcbiFetchError`, `NcbiRecordRejected`, and `FastaWriteError` exit `1`. |
| `test_all_blank_table_exits_0` | An all-blank table exits `0` with zero fetches. |
| `test_cached_and_blank_table_exits_0_and_prints_summary` | CLI exits `0` and prints `skipped`, `cached`, and `fetched` lines. |
| `test_written_paths_print_before_the_summary` | Each newly written path is printed before the summary lines. |
| `test_entrez_config_sets_ncbi_fasta_tool_and_optional_key` | `entrez_config_from_environment` sets `tool="virus_redteaming_ncbi_fasta"` and redacts `api_key` in `repr`. |
| `test_empty_api_key_is_omitted` | An unset or empty `NCBI_API_KEY` is omitted (`api_key is None`). |

One offline integration test reads `output/HSE-virus_Cat1-virus_merged.csv` and does not call NCBI. It asserts 33 blank rows, 727 distinct codes, that the influenza A cell `RNA1: V00603; RNA2: J02151` yields those two codes first, and that `GenBankSegmentParser.codes` equals `GenBankAccessionParser.codes` on every row while `join` equals the `NCBI accession` cell.

A live Entrez test is opt-in. It runs only when `NCBI_LIVE_TEST=1` and `NCBI_EMAIL` are both set, fetches `V00603` into a temporary directory, checks that the file name is `V00603.fasta` and that the header contains `V00603.1`, and is marked `network`.

## Out of scope

The merged CSV stays unchanged. `RefSeq accessions` is unread. This command makes no `esearch` call. `clinical_fasta` search and `output/clinical_genes/` stay as they are.
