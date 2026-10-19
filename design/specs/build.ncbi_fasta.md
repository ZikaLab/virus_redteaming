# build.ncbi_fasta.md

**Status:** accepted  
**Spec:** [spec.ncbi_fasta.md](spec.ncbi_fasta.md)  
**Target:** `fetch-ncbi-fasta` reads `GenBank accessions` from `--csv` (default `output/HSE-virus_Cat1-virus_merged.csv`) and writes `output/NCBI_fasta/{accession}.fasta`

## Execution rule

Reading this file does not create Python. A request to run this build creates or updates the modules and tests below, then runs the unit and offline integration tests. It calls NCBI only when `NCBI_LIVE_TEST=1` and `NCBI_EMAIL` are both set.

## 0. Locked rules

| Rule | Value |
| --- | --- |
| Database | `nuccore` (`Bio.Entrez.efetch`, `rettype="fasta"`, `retmode="text"`) |
| Input CSV flag | `--csv` (default `output/HSE-virus_Cat1-virus_merged.csv`) |
| Output directory flag | `--out` (default `output/NCBI_fasta`) |
| Source column | `GenBank accessions` |
| Blank cell | Skipped and counted in `blank_rows` |
| Segment separator | `;` (a trailing empty piece after a terminal `;` is dropped; an empty middle piece is `NcbiFastaInputError`) |
| Label separator | First `:` in a segment (`label: code`). Empty label before `:` is `NcbiFastaInputError` |
| Coordinate suffix | Trailing `\s*\(\d+\.\d+\)\s*$` stripped from the code |
| Accession pattern | `^(?:[A-Z]{2}_\d{6,9}|[A-Z]{2}\d{8}|[A-Z]{2}\d{6}|[A-Z]\d{5})(?:\.\d+)?$` |
| Deduplication | First-seen order within each row and across the table (`727` distinct codes across `391` populated rows) |
| Length cutoff | None — every viral genome segment length is written |
| Cache hit rule | `{out}/{accession}.fasta` is a regular UTF-8 file that `Bio.SeqIO.parse` parses as 1 record with `len(record.seq) > 0` and `AccessionIdentity.matches(record, accession)` |
| Entrez tool | `virus_redteaming_ncbi_fasta` |
| Email | `NCBI_EMAIL`, required, no whitespace (missing/whitespace exits `2`) |
| API key | `NCBI_API_KEY`, optional, omitted when empty, redacted from `repr` and errors |

## 1. SOLID map

| Principle | How |
| --- | --- |
| S | Segment parsing (`GenBankSegmentParser`), CSV scanning (`MergedGenBankSource`), local cache validation (`DirectoryFastaCache`), Entrez config construction (`entrez_config_from_environment`), and download orchestration (`NcbiFastaDownload`) are separate types |
| O | New segment grammars or cache stores implement `SegmentParser` or `FastaCache` without modifying `NcbiFastaDownload` |
| L | Fakes in `tests/unit/ncbi_fasta/` honor `SegmentParser`, `GenBankSource`, `FastaCache`, and `NucleotideFetch` |
| I | `SegmentParser`, `GenBankSource`, and `FastaCache` each have a single method |
| D | `NcbiFastaDownload` depends only on Protocols (`GenBankSource`, `FastaCache`, `FastaRecordSource`, `FastaEncoder`, `FastaSink`) and imports neither `csv` nor `Bio` |

Package: `src/virus_redteaming/ncbi_fasta/`. CLI entrypoint: `src/virus_redteaming/__main__.py` (`fetch-ncbi-fasta`).

## 2. Reused types from `clinical_fasta`

Inject these directly without copying them:

| Type | Module | Role |
| --- | --- | --- |
| `NcbiEntrezConfig` | `clinical_fasta/config.py` | Validates `email` and redacts `api_key` |
| `BiopythonEntrezClient` | `clinical_fasta/biopython_entrez.py` | Performs `Bio.Entrez.efetch` (`db="nuccore"`, `rettype="fasta"`, `retmode="text"`) |
| `AccessionIdentity` | `clinical_fasta/fasta_source.py` | Matches requested stem and optional version against FASTA header tokens |
| `FastaFetchSource` | `clinical_fasta/fasta_source.py` | Parses one non-empty `SeqRecord` from `NucleotideFetch` that `AccessionIdentity` accepts |
| `BiopythonFastaEncoder` | `clinical_fasta/fasta_encoder.py` | Serializes `SeqRecord` to FASTA text under the requested accession |
| `AtomicPathFastaSink` | `clinical_fasta/sink.py` | Atomically writes `{out}/{accession}.fasta` via temp file + `os.replace` |

## 3. Pseudocode per module

### 3.1 `ncbi_fasta/errors.py`

```text
NcbiFastaInputError(VirusRedteamingError)
    raised when:
      - the CSV path is missing or not a regular file
      - the CSV header lacks "GenBank accessions"
      - a populated cell has an empty segment, an empty label before ":",
        or a code that fails the accession pattern
```

### 3.2 `ncbi_fasta/models.py`

```text
GenBankTableScan (frozen dataclass)
    codes: tuple[str, ...]
    blank_rows: int

FetchNcbiFastaReport (frozen dataclass)
    written: tuple[Path, ...]
    cached: tuple[Path, ...]
    blank_rows: int
```

### 3.3 `ncbi_fasta/protocols.py`

```text
SegmentParser(Protocol)
    codes(cell: str) -> tuple[str, ...]

GenBankSource(Protocol)
    read() -> GenBankTableScan

FastaCache(Protocol)
    cached(accession: str) -> Path | None
```

### 3.4 `ncbi_fasta/config.py`

```text
TOOL = "virus_redteaming_ncbi_fasta"

entrez_config_from_environment() -> NcbiEntrezConfig
    email <- os.environ.get("NCBI_EMAIL", "")
    raw_key <- os.environ.get("NCBI_API_KEY", "")
    api_key <- raw_key if raw_key else None
    return NcbiEntrezConfig(email=email, tool=TOOL, api_key=api_key)
```

### 3.5 `ncbi_fasta/parse.py`

```text
_ACCESSION = r"^(?:[A-Z]{2}_\d{6,9}|[A-Z]{2}\d{8}|[A-Z]{2}\d{6}|[A-Z]\d{5})(?:\.\d+)?$"
_COORDINATE = r"\s*\(\d+\.\d+\)\s*$"

GenBankSegmentParser
    codes(cell: str) -> tuple[str, ...]
        text <- cell.replace("\xa0", " ").strip()
        if text is empty:
            return ()
        pieces <- text.split(";")
        if pieces[-1].strip() is empty:
            pieces <- pieces[:-1]
        seen <- []
        for piece in pieces:
            segment <- piece.strip()
            if segment is empty:
                raise NcbiFastaInputError("GenBank cell has an empty segment")
            if ":" in segment:
                label, raw_code <- segment.split(":", 1)
                if label.strip() is empty:
                    raise NcbiFastaInputError("GenBank segment label is empty")
            else:
                raw_code <- segment
            code <- strip trailing _COORDINATE from raw_code.strip()
            if not _ACCESSION.fullmatch(code):
                raise NcbiFastaInputError(f"GenBank accession is not valid: {code}")
            if code not in seen:
                seen.append(code)
        return tuple(seen)
```

### 3.6 `ncbi_fasta/source.py`

```text
_COLUMN = "GenBank accessions"

MergedGenBankSource(path: Path, parser: SegmentParser)
    read() -> GenBankTableScan
        if not path.is_file():
            raise NcbiFastaInputError("merged table is missing")
        seen <- []
        blank_rows <- 0
        open path as UTF-8 csv.DictReader:
            if fieldnames is None or _COLUMN not in fieldnames:
                raise NcbiFastaInputError("GenBank accessions header is missing")
            for record in reader:
                raw <- record.get(_COLUMN)
                cell <- (raw if raw is not None else "").replace("\xa0", " ").strip()
                if cell is empty:
                    blank_rows += 1
                    continue
                for code in parser.codes(cell):
                    if code not in seen:
                        seen.append(code)
        return GenBankTableScan(tuple(seen), blank_rows)
```

### 3.7 `ncbi_fasta/cache.py`

```text
DirectoryFastaCache(directory: Path, identity: AccessionIdentity)
    cached(accession: str) -> Path | None
        path <- directory / f"{accession}.fasta"
        if not path.is_file():
            return None
        try:
            open path with encoding="utf-8" and parse with SeqIO.parse(handle, "fasta")
        except Exception:
            return None
        if len(records) != 1:
            return None
        record <- records[0]
        if len(record.seq) == 0 or not identity.matches(record, accession):
            return None
        return path
```

### 3.8 `ncbi_fasta/workflow.py`

```text
NcbiFastaDownload(
    source: GenBankSource,
    cache: FastaCache,
    records: FastaRecordSource,
    encoder: FastaEncoder,
    sink: FastaSink,
)
    run() -> FetchNcbiFastaReport
        scan <- source.read()
        written <- []
        cached <- []
        for code in scan.codes:
            hit <- cache.cached(code)
            if hit is not None:
                cached.append(hit)
                continue
            record <- records.fetch(code)
            written.append(sink.write(encoder.encode(code, record)))
        return FetchNcbiFastaReport(tuple(written), tuple(cached), scan.blank_rows)
```

### 3.9 `src/virus_redteaming/__main__.py`

```text
subparser "fetch-ncbi-fasta":
    --csv: Path = Path("output/HSE-virus_Cat1-virus_merged.csv")
    --out: Path = Path("output/NCBI_fasta")

_print_ncbi_fasta(csv_path: Path, out_dir: Path) -> int
    try:
        report <- _fetch_ncbi_fasta(csv_path, out_dir)
    except NcbiConfigError as exc:
        print exc to stderr; return 2
    except VirusRedteamingError as exc:
        print exc to stderr; return 1
    for path in report.written:
        print(path)
    print(f"skipped {report.blank_rows} blank rows")
    print(f"cached {len(report.cached)} accessions")
    print(f"fetched {len(report.written)} accessions")
    return 0

_fetch_ncbi_fasta(csv_path: Path, out_dir: Path) -> FetchNcbiFastaReport
    identity <- AccessionIdentity()
    client <- BiopythonEntrezClient(entrez_config_from_environment())
    return NcbiFastaDownload(
        source=MergedGenBankSource(csv_path, GenBankSegmentParser()),
        cache=DirectoryFastaCache(out_dir, identity),
        records=FastaFetchSource(client, identity),
        encoder=BiopythonFastaEncoder(),
        sink=AtomicPathFastaSink(out_dir),
    ).run()
```

## 4. Call order

```text
python -m virus_redteaming fetch-ncbi-fasta --csv PATH --out DIR
  -> entrez_config_from_environment() -> NcbiEntrezConfig (or NcbiConfigError -> exit 2)
  -> MergedGenBankSource.read()
       -> GenBankSegmentParser.codes(cell) for each non-blank row
       -> GenBankTableScan(codes, blank_rows)
  -> for each distinct code in scan.codes:
       -> DirectoryFastaCache.cached(code)
            -> if valid single-record FASTA matching AccessionIdentity: append to cached
            -> else:
                 -> BiopythonEntrezClient.fetch_fasta(code)
                 -> FastaFetchSource.fetch(code) (validates 1 record, non-empty seq, AccessionIdentity)
                 -> BiopythonFastaEncoder.encode(code, record)
                 -> AtomicPathFastaSink.write(fasta_record) -> {DIR}/{code}.fasta
                 -> append to written
  -> print each written path, then skipped/cached/fetched counts -> exit 0
```

## 5. Tests

Unit tests live in `tests/unit/ncbi_fasta/`. They use fakes and `tmp_path` and never call NCBI.

| File | Test function | Asserts |
| --- | --- | --- |
| `test_parse.py` | `test_labelled_segments_keep_the_code_after_each_colon` | `RNA1: V00603; RNA2: J02151` -> `("V00603", "J02151")` |
| `test_parse.py` | `test_bare_accession_is_kept` | `U87411` and `AF052015;` keep the code |
| `test_parse.py` | `test_coordinate_suffix_is_stripped_after_colon` | `Seg1: AH009795(1.3949); Seg4: AF403390` -> `("AH009795", "AF403390")` |
| `test_parse.py` | `test_wgs_accession_is_rejected` | `CASDWV010000980` raises `NcbiFastaInputError` |
| `test_parse.py` | `test_repeated_code_inside_one_cell_is_kept_once` | `AF052015; AF052015` -> `("AF052015",)` |
| `test_parse.py` | `test_blank_and_nbsp_cells_are_empty_or_stripped` | Whitespace and a U+00A0-only cell return `()`. U+00A0 around a code is stripped. |
| `test_parse.py` | `test_malformed_populated_cell_raises_input_error` | `;`, `No entry in Genbank`, `RNA1: ???`, `: V00603`, `L: V00603; ; S: J02151` raise `NcbiFastaInputError` |
| `test_parse.py` | `test_other_segment_labels_keep_the_code` | `L:`, `S:`, `Seg1:`, `DNA-C:`, `DNA-M:` labels keep their codes |
| `test_source.py` | `test_blank_genbank_cell_is_skipped` | Blank cell increments `blank_rows` and emits no code |
| `test_source.py` | `test_repeated_accession_across_rows_is_scheduled_once` | Duplicate codes across rows appear once in first-seen order |
| `test_source.py` | `test_missing_genbank_header_raises_input_error` | Missing `GenBank accessions` column raises `NcbiFastaInputError` |
| `test_source.py` | `test_missing_file_raises_input_error` | Missing CSV path raises `NcbiFastaInputError` |
| `test_source.py` | `test_directory_path_raises_input_error` | A directory path raises `NcbiFastaInputError` |
| `test_source.py` | `test_short_row_and_nbsp_blank_are_skipped` | A short row (`None` cell) and a U+00A0-only cell increment `blank_rows`. A U+00A0 before a code is stripped. |
| `test_cache.py` | `test_missing_file_returns_none` | Missing `.fasta` file returns `None` |
| `test_cache.py` | `test_valid_single_record_is_a_hit` | Valid single-record FASTA matching stem returns path |
| `test_cache.py` | `test_empty_or_non_fasta_file_returns_none` | Empty file or non-FASTA text returns `None` |
| `test_cache.py` | `test_multiple_records_return_none` | Multi-record FASTA file returns `None` |
| `test_cache.py` | `test_unreadable_utf8_bytes_return_none` | Invalid UTF-8 bytes return `None` |
| `test_download.py` | `test_valid_cached_fasta_file_is_a_cache_hit` | Cached file skips `fetch_fasta` |
| `test_download.py` | `test_header_only_or_mismatched_cached_file_is_refetched` | Empty-sequence or wrong-stem cached file is re-fetched and replaced |
| `test_download.py` | `test_versioned_header_matches_unversioned_request` | `V00603` matches `>emb\|V00603.1\|`; `AF291704` matches `>AF291704.5` |
| `test_download.py` | `test_older_cached_version_is_a_hit` | `>AF291704.1` is a cache hit for unversioned `AF291704` |
| `test_download.py` | `test_different_header_stem_is_rejected` | `>NC_002023.1` for `V00603` raises `NcbiRecordRejected` |
| `test_download.py` | `test_conflicting_versions_are_rejected` | `>V00603.2` for `V00603.1` raises `NcbiRecordRejected` |
| `test_download.py` | `test_short_sequence_is_written` | 2341 bp segment is written without length filtering |
| `test_download.py` | `test_missing_genbank_header_raises_input_error` | Missing column fails before any fetch |
| `test_download.py` | `test_interrupted_run_resumes_without_refetching_earlier_files` | First written file stays on disk when second fails, and is cached on retry |
| `test_workflow.py` | `test_protocol_fakes_skip_cached_codes_and_stop_on_fetch_error` | Injected `GenBankSource`, `FastaCache`, `FastaRecordSource`, `FastaEncoder`, and `FastaSink` fakes: a cache hit is not fetched; a later fetch error is not encoded or written and stops the run |
| `test_cli.py` | `test_missing_email_exits_2` | Missing `NCBI_EMAIL` exits `2` |
| `test_cli.py` | `test_whitespace_email_exits_2` | `NCBI_EMAIL` containing whitespace exits `2` |
| `test_cli.py` | `test_bad_table_exits_1` | Missing `GenBank accessions` header exits `1` |
| `test_cli.py` | `test_fetch_and_write_errors_exit_1` | `NcbiFetchError`, `NcbiRecordRejected`, and `FastaWriteError` from the assembled command exit `1` |
| `test_cli.py` | `test_all_blank_table_exits_0` | An all-blank table exits `0` with zero cached and zero fetched |
| `test_cli.py` | `test_cached_and_blank_table_exits_0_and_prints_summary` | Valid run exits `0` and prints `skipped`, `cached`, and `fetched` counts |
| `test_cli.py` | `test_written_paths_print_before_the_summary` | Each newly written path is printed before the summary lines |
| `test_cli.py` | `test_entrez_config_sets_ncbi_fasta_tool_and_optional_key` | Sets `tool="virus_redteaming_ncbi_fasta"` and redacts `api_key` |
| `test_cli.py` | `test_empty_api_key_is_omitted` | Unset or empty `NCBI_API_KEY` yields `api_key is None` |

Integration tests:

- `tests/integration/test_ncbi_fasta_table.py` (offline): reads `output/HSE-virus_Cat1-virus_merged.csv` and verifies `33` blank rows, `727` distinct codes, `RNA1: V00603; RNA2: J02151` -> `("V00603", "J02151")`, and `GenBankSegmentParser.codes == GenBankAccessionParser.codes` on all 424 rows.
- `tests/integration/test_ncbi_fasta_live.py` (`@pytest.mark.network`): opt-in live test (`NCBI_LIVE_TEST=1` and `NCBI_EMAIL`), fetches `V00603` into `tmp_path` and checks `V00603.fasta` starts with `>V00603.1`.

```bash
.venv/bin/python -m pytest tests/unit/ncbi_fasta tests/integration/test_ncbi_fasta_table.py -q
```
