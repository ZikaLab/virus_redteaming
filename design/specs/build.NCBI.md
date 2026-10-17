# build.NCBI.md

**Status:** proposed  
**Companion spec:** [spec.NCBI.md](spec.NCBI.md)  
**Target:** part 1 writes `output/accessions.csv`; part 2 writes `output/clinical_genes/{accession}.fasta`  
**Scope:** clinical genes and genomes are not pathogen work (ADR 0004); pathogen genomes remain prohibited.

## Execution rule

Reading or editing this file does **not** create Python.

A request to **run this build** (this document named, or “run `build.NCBI.md`”) **does** create the modules and the Pytest files in §2 and §4, then runs the unit tests in §4. It does not call NCBI unless `NCBI_LIVE_TEST=1` and `NCBI_EMAIL` are both set.

Do not put this workflow in `catalogue/`. Do not import pdfplumber. Do not hard-code a query phrase. The term is composed at run time from the selected CSV and `output/search.txt`.

## 0. Locked rules

| Rule | Value |
| --- | --- |
| Database | `nuccore` only |
| Accessions per `Virus` cell | 5 (`retmax=5`, `retstart=0`) |
| Length cutoff | `len(sequence) > cutoff`. Default `LengthCutoff.DEFAULT_BP = 8000` in `length.py` |
| Query | A cell with no field flag: `"{trimmed Virus cell}" AND {search.txt line} AND {bp + 1}:{MAX_SLEN}[SLEN]`. A field flag is placed after the closing quote, as in `"human"[organism]`. |
| Part 1 output | `output/accessions.csv` header `Virus,Rank,Accession` |
| Part 2 output | `output/clinical_genes/{requested accession}.fasta` |
| Email | `NCBI_EMAIL`, required, no whitespace |
| API key | `NCBI_API_KEY`, omitted from the call when empty, never logged |

Part 1 calls `Bio.Entrez.esearch` only. Part 2 calls `Bio.Entrez.efetch` only, with `rettype=fasta` and `retmode=text`, and no `term`.

## 1. SOLID map

| Principle | How |
| --- | --- |
| S | Path, CSV source, search-term source, term composer, search client, accession list, accession sink, accession source, identity, length, fetch source, encoder, FASTA sink, and the two workflows are separate types |
| O | A new FASTA check implements `AccessionIdentity` or `LengthCutoff` without editing the Entrez client |
| L | Unit-test fakes honour `NucleotideSearcher` and `FastaRecordSource` |
| I | Part 1 does not depend on FASTA types. Part 2 does not depend on the term composer |
| D | `AccessionSearch` and `ClinicalFastaDownload` depend on Protocols. Biopython lives only in `BiopythonEntrezClient`, `FastaFetchSource`, and `BiopythonFastaEncoder` |

Package: `src/virus_redteaming/clinical_fasta/`. Entrypoint: `clinical_fasta/__main__.py`. The catalogue entrypoint `virus_redteaming/__main__.py` stays unchanged.

Dependency: `biopython>=1.86,<2`. Register it in `pyproject.toml` as described in §5.

## 2. Pseudocode per module

### 2.1 `clinical_fasta/errors.py`

One package base. Subclasses, and nothing else, are raised:

```
NcbiInputError        bad CSV, bad search.txt, bad accession text
NcbiConfigError       email missing or containing whitespace
NcbiSearchMiss        empty IdList, or an IdList item that is not a non-empty string
NcbiFetchError        transport, HTTP failure, exhausted retry, unreadable esearch body
NcbiRecordRejected    FASTA count, identity, empty sequence, or length
FastaWriteError       atomic replace of the accession table or a FASTA file failed
```

Exception text, logs, and `repr` must not contain the API key.

### 2.2 `clinical_fasta/models.py`

```
AccessionHit        frozen: virus cell, rank, accession
FastaRecord         frozen: accession, FASTA text
```

### 2.2a `clinical_fasta/protocols.py`

Protocols only. No Biopython import except `SeqRecord` on the two signatures that already return or accept it.

```
VirusQuerySource.read() → tuple[str, ...]
SearchTermSource.read() → str
NucleotideSearcher.search(term) → tuple[str, ...]
AccessionTableSink.write(hits) → Path
AccessionTableSource.read() → tuple[str, ...]
NucleotideFetch.fetch_fasta(accession) → str
FastaRecordSource.fetch(accession) → SeqRecord
FastaEncoder.encode(accession, record) → FastaRecord
FastaSink.write(record) → Path
```

`NucleotideFetch` is the seam between `FastaFetchSource` and `BiopythonEntrezClient`. The client implements both `NucleotideSearcher` and `NucleotideFetch`.

### 2.3 `clinical_fasta/config.py`

```
NcbiEntrezConfig.from_environment()
    email ← NCBI_EMAIL
    reject if missing or if email contains whitespace → NcbiConfigError
    api_key ← NCBI_API_KEY when non-empty, else absent
    tool ← "virus_redteaming_clinical_fasta"
    repr and str redact api_key
```

Before every Entrez call, assign `Bio.Entrez.email`, `Bio.Entrez.tool`, and, when a key is configured, `Bio.Entrez.api_key` from this config. Biopython's rate limiter and the missing-email warning read those module attributes. A key passed only as a call argument does not raise the limit from 3 requests per second to 10. When no key is configured, set `Bio.Entrez.api_key` to `None` and do not pass `api_key` on the call. Do not assign `Bio.Entrez.max_tries` or `Bio.Entrez.sleep_between_tries`. Calls stay serial, so the process-wide attributes are not shared across threads.

### 2.4 `clinical_fasta/paths.py`

```
OutputCsvPath(filename)
    reject empty, absolute, leading ".", "/", "\", or ".."
    resolve to {repo}/output/{filename}
```

### 2.5 `clinical_fasta/length.py`

```
LengthCutoff
    DEFAULT_BP = 8000
    MAX_SLEN = 999999999
    docstring: change LengthCutoff.DEFAULT_BP in this module when the default cutoff changes.
               change LengthCutoff.MAX_SLEN in this module when the search upper bound changes.
               search --min-length and download --min-length override DEFAULT_BP for one run
               and do not edit DEFAULT_BP.
    __init__(bp: int = DEFAULT_BP)
    accepts(sequence_length) → sequence_length > bp
    slen_clause() → "{bp + 1}:{MAX_SLEN}[SLEN]"
```

### 2.6 `clinical_fasta/csv_source.py`

```
OutputCsvVirusSource(path).read() → tuple[str, ...]
    UTF-8 csv
    require a header cell exactly "Virus" else NcbiInputError
    yield trimmed Virus cells in file order
    skip blanks
    zero non-blank cells → NcbiInputError
    missing file or not a regular file → NcbiInputError
```

### 2.7 `clinical_fasta/search_term.py`

```
OutputSearchTermSource(path).read() → str
    path is injected. The CLI passes {repo}/output/search.txt. Tests pass tmp_path.
    UTF-8
    drop one trailing newline
    strip
    exactly one non-empty line
    empty, whitespace-only, or a second non-empty line → NcbiInputError
    reject a line containing " [ ] ( )
```

### 2.8 `clinical_fasta/term.py`

```
EntrezTermComposer.compose(virus, extra, cutoff) → str
    reject virus if it contains " → NcbiInputError
    if the trimmed cell contains [ or ]: quote each field value and place the flag after the closing quote
    otherwise return '"' + trimmed virus + '" AND ' + extra + ' AND ' + cutoff.slen_clause()
    do not append an accession
    do not substitute a stored phrase
```

### 2.9 `clinical_fasta/biopython_entrez.py`

```
BiopythonEntrezClient(config)
    search(term) → tuple[str, ...]
        Entrez.esearch(db="nuccore", term=term, retmax=5, retstart=0, idtype="acc", tool, email, api_key?)
        Bio.Entrez.read the handle, then close it
        return IdList in NCBI order
        do not drop, reorder, or prefer an accession
        do not call efetch

    fetch_fasta(accession) → str
        Entrez.efetch(db="nuccore", id=accession, rettype="fasta", retmode="text", tool, email, api_key?)
        no term argument
        read the handle to text, then close it, then return the text
        the caller never sees the handle
```

`Bio.Entrez` owns rate limiting and retries. This type does not add a second retry loop. HTTP 429 is not retried. A 429, a non-retried 4xx, an exhausted 5xx retry, a timeout, a transport failure, or an esearch body `Bio.Entrez.read` cannot parse is `NcbiFetchError`.

### 2.10 `clinical_fasta/accession_list.py`

```
AccessionList.keep(ids) → tuple[str, ...]
    empty, or any item that is not a non-empty string → NcbiSearchMiss
    if more than 5, keep the first 5
    else keep every item, in order
```

### 2.11 `clinical_fasta/accession_sink.py`

```
AtomicAccessionTableSink(destination).write(hits) → Path
    destination is injected. The CLI passes {repo}/output/accessions.csv. Tests pass tmp_path.
    write a uniquely named temp file in destination's directory
    header Virus,Rank,Accession
    one row per hit; Rank is 1-based and restarts at 1 for each Virus cell
    Accession is the IdList string unchanged
    flush, close, os.replace onto destination
    on failure before replace: delete the temp file and leave the previous destination in place
    persistence failure → FastaWriteError
```

Publish when at least one `Virus` cell has a non-empty list. A cell with no hits is omitted and returned as a miss. If every cell has no hits, do not replace the file.

### 2.12 `clinical_fasta/accession_source.py`

```
AccessionCsvSource(path).read() → tuple[str, ...]
    path is injected. The CLI passes {repo}/output/accessions.csv. Tests pass tmp_path.
    require that file and an Accession header
    zero data rows → NcbiInputError
    strip each accession
    reject unless it matches ^[A-Z]{1,6}_?[0-9]+(\.[0-9]+)?$
    a bad id is NcbiInputError and is not fetched
    return distinct ids in first-seen order
```

### 2.13 `clinical_fasta/fasta_source.py`

```
AccessionIdentity.matches(record, requested) → bool
    candidates ← record.id, each "|" piece of record.id, record.name
    ignore the description
    a candidate matches only when both sides parse as
        ^[A-Z]{1,6}_?[0-9]+(\.[0-9]+)?$
    stems must be equal
    if both sides have a version, the versions must be equal
    a missing version on one side still matches
    NG_007114 matches NG_007114.1
    NG_007114.1 matches itself
    NG_007114.1 does not match NG_007114.2
    NG_007114.1 does not match NG_007114.1.2

FastaFetchSource(client: NucleotideFetch, identity).fetch(accession) → SeqRecord
    text ← client.fetch_fasta(accession)
    SeqIO.parse(StringIO(text), "fasta") must yield exactly one record
    zero, many, or a parser exception → NcbiRecordRejected
    identity.matches is false → NcbiRecordRejected
    sequence empty → NcbiRecordRejected
    this type does not apply the length cutoff and does not open an output file
```

### 2.14 `clinical_fasta/fasta_encoder.py`

```
BiopythonFastaEncoder.encode(accession, record) → FastaRecord
    the only type that calls Bio.SeqIO.write
    write the one record to memory
    FASTA text ends with one newline
    FastaRecord.accession is the accession argument, not record.id
```

### 2.15 `clinical_fasta/sink.py`

```
AtomicPathFastaSink(directory).write(record) → Path
    directory is injected. The CLI passes {repo}/output/clinical_genes. Tests pass tmp_path.
    create that directory if missing
    destination is {directory}/{record.accession}.fasta
    temp file, flush, close, os.replace
    failure before replace: delete the temp file; do not change that destination
    earlier accessions already replaced in this run stay on disk
    persistence failure → FastaWriteError
```

### 2.16 `clinical_fasta/search_workflow.py`

```
AccessionSearch(viruses, extra_term, composer, searcher, accession_list, cutoff, sink)
    docstring does not contain a query phrase
    run() → SearchResult(path, misses)
        extra ← extra_term.read()
        hits ← []
        misses ← []
        for each virus in viruses.read(), in order:
            term ← composer.compose(virus, extra, cutoff)
            ids ← accession_list.keep(searcher.search(term))
            if ids is empty: append virus to misses and continue
            append AccessionHit(virus, rank, id) for rank starting at 1
        if hits is empty → NcbiSearchMiss
        return SearchResult(sink.write(hits), misses)
    this type does not open a socket and does not write FASTA
```

A cell with no hits is omitted and included in `SearchResult.misses`. The CLI prints `no accessions for Virus cell: {cell}` to stderr for each miss and exits 1. `NcbiSearchMiss` is raised only when every cell has no hits, or when an `IdList` item is not a non-empty string. That raise happens before `sink.write`.

### 2.17 `clinical_fasta/download_workflow.py`

```
ClinicalFastaDownload(accessions, source, cutoff, encoder, sink)
    docstring names LengthCutoff.DEFAULT_BP in length.py
    and says --min-length overrides that default for one run
    run() → tuple[Path, ...]
        paths ← []
        for accession in accessions.read():
            record ← source.fetch(accession)
            if not cutoff.accepts(len(record.seq)):
                continue
            paths.append(sink.write(encoder.encode(accession, record)))
        if paths is empty → NcbiRecordRejected
        return tuple(paths)
    a short record is skipped. It is not a failed fetch.
    parse, identity, and empty-sequence failures still raise and stop the run
    this type does not open a socket and does not search
```

### 2.18 `clinical_fasta/__main__.py`

```
python -m virus_redteaming.clinical_fasta search
    filename ← genes.csv
python -m virus_redteaming.clinical_fasta search {filename} --min-length N
    filename ← {filename}
    cutoff ← N when the flag is present, else LengthCutoff.DEFAULT_BP
    read output/{filename} and output/search.txt
    print the accessions.csv path
    print each empty Virus cell to stderr
    exit 1 when any Virus cell returned no accessions
    exit 0 when every Virus cell returned at least one accession

python -m virus_redteaming.clinical_fasta download
    cutoff ← LengthCutoff.DEFAULT_BP
python -m virus_redteaming.clinical_fasta download --min-length N
    N is an integer ≥ 0, else usage error exit 2
    cutoff ← N for this run only
    print each kept FASTA path, one per line
    skip accessions whose sequence is not longer than the cutoff
    exit 0 when at least one accession is written
    exit 1 when every accession is skipped for length

missing email or email with whitespace → stderr, exit 2
NcbiConfigError or a bad argument → stderr, exit 2
any other package error → stderr, exit 1
no --complete-genome, no --db, no raw term argument
download takes no query filename; its only option is --min-length
the download function docstring names LengthCutoff.DEFAULT_BP in length.py
```

## 3. Call order

```
part 1
  output/{csv} + output/search.txt
    → OutputCsvVirusSource.read()
    → OutputSearchTermSource.read()
    → for each Virus cell:
          EntrezTermComposer.compose(virus, extra, cutoff)
          BiopythonEntrezClient.search
          AccessionList.keep
          skip an empty IdList
    → AtomicAccessionTableSink.write → output/accessions.csv

part 2
  output/accessions.csv
    → AccessionCsvSource.read()
    → LengthCutoff(DEFAULT_BP or --min-length)
    → for each distinct accession:
          NucleotideFetch.fetch_fasta → text, handle already closed
          FastaFetchSource.fetch → SeqRecord
          skip when LengthCutoff.accepts is false
          BiopythonFastaEncoder.encode(accession, record)
          AtomicPathFastaSink.write → {directory}/{accession}.fasta
```

## 4. Tests

Unit tests live in `tests/unit/clinical_fasta/`. They use Protocol fakes and do not call NCBI.

| Test | Asserts |
| --- | --- |
| `test_csv_path_resolves_under_output` | A bare filename resolves under `output/`. `../secrets.csv`, `/tmp/x.csv`, and `a/b.csv` raise `NcbiInputError`. |
| `test_csv_reads_virus_column_in_order` | A non-blank cell, a blank cell, then another non-blank cell yield those two trimmed cells in order. |
| `test_csv_rejects_missing_virus_header` | A header without `Virus` raises `NcbiInputError`. |
| `test_csv_rejects_all_blank_virus_cells` | Header only, or only blank `Virus` cells, raises `NcbiInputError`. |
| `test_search_txt_reads_the_single_line` | One non-empty line, after dropping a trailing newline and surrounding whitespace, is the extra term. |
| `test_search_txt_rejects_empty_and_multiple_terms` | Empty, whitespace-only, and two non-empty lines raise `NcbiInputError`. |
| `test_term_composer_quotes_virus_and_ands_extra` | A cell with no brackets returns `"{Virus}" AND {extra} AND {bp + 1}:{MAX_SLEN}[SLEN]`, with no accession and no `[Accession]`. |
| `test_term_composer_sends_field_query_unquoted` | `human[organism] mitochondrion genome` is sent as `"human"[organism] mitochondrion genome`. |
| `test_field_query_keeps_all_five_hits` | That field query is the term sent to search. All five returned accessions are written. |
| `test_download_writes_all_five_mitochondrion_genomes` | Those five accessions, each longer than the cutoff, are all written. |
| `test_term_composer_rejects_embedded_quotes` | A `Virus` cell containing `"` raises `NcbiInputError`. |
| `test_search_keeps_first_5_in_order` | An 8-id response writes ranks 1–5 in response order. A 3-id response writes ranks 1–3. |
| `test_search_miss_does_not_publish_accession_file` | One empty `IdList` is omitted, reported on the result, and the other cell is written. When every cell is empty, `NcbiSearchMiss` is raised and an existing accession file is not replaced. |
| `test_search_does_not_call_efetch` | Part 1 calls esearch with `retmax=5`, `retstart=0`, and `idtype=acc`. It does not call efetch. |
| `test_download_fetches_each_distinct_accession_as_fasta` | Accessions A1, A2, A1 produce two `fetch_fasta` calls, ids A1 then A2. The client test checks `rettype=fasta`, `retmode=text`, no term, and that the handle is closed before the text is returned. |
| `test_download_rejects_malformed_accession` | An id outside the §2.12 pattern raises `NcbiInputError` and does not call efetch. |
| `test_fasta_source_accepts_one_matching_record` | One FASTA record whose id equals the requested accession is returned from text supplied by a `NucleotideFetch` fake. |
| `test_fasta_identity_accepts_version_and_bar_token` | Requested `NG_007114` matches `NG_007114.1` and `ref\|NG_007114.1\|`. `NG_007114.1` does not match `NG_007114.2` or `NG_007114.1.2`. |
| `test_fasta_source_rejects_wrong_count_or_id` | Zero records, two records, a mismatched accession, or an empty sequence raises `NcbiRecordRejected`. |
| `test_length_cutoff_default_is_8000_and_is_exclusive` | `LengthCutoff.DEFAULT_BP` is 8000. `MAX_SLEN` is the search upper bound. Length 8000 is rejected. Length 8001 is accepted. The SLEN clause is `8001:{MAX_SLEN}[SLEN]`. |
| `test_download_min_length_overrides_default` | `--min-length 10000` skips a 9000 bp record, writes a later record longer than 10000 bp, and does not change `LengthCutoff.DEFAULT_BP`. |
| `test_download_skips_short_records_and_fails_when_none_remain` | A short record followed by a long one writes only the long one. A run where every record is short raises `NcbiRecordRejected` and writes nothing. |
| `test_entrez_client_omits_unset_api_key` | With no key, neither call receives `api_key`. With a key, that key is passed on both. |
| `test_sink_replaces_atomically_and_removes_temp_on_failure` | Success leaves no temporary file. A failure before `os.replace` deletes the temporary file and leaves an existing destination unchanged. |
| `test_errors_and_logs_redact_api_key` | The API key does not appear in exception text, logs, or object representation. |

An integration test that calls NCBI is opt-in only. It requires `NCBI_LIVE_TEST=1` and `NCBI_EMAIL`, and is marked network. It reads the selected CSV and `output/search.txt`, sends only the composed term, and uses `retmax=5`. It must not embed a query string. Setting an email must not make the unit tests use the network.

```bash
python3 -m pytest tests/unit/clinical_fasta -q
```

## 5. Packaging

Running this build also updates `pyproject.toml`:

| Change | Why |
| --- | --- |
| Add `biopython>=1.86,<2` to `dependencies` | The Entrez client and FASTA encoder import Biopython. |
| Register a `network` marker under `[tool.pytest.ini_options]` | `addopts` already sets `--strict-markers`. An unregistered `network` mark fails collection. |
| Add a mypy override with `ignore_missing_imports` for `Bio` and `Bio.*` | `mypy --strict` is on, and Biopython does not ship a complete strict stub set. |
