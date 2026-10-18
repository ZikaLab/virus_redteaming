# spec.NCBI.md

**Status:** proposed (spec only; no implementation in this change)  
**Build:** [build.NCBI.md](build.NCBI.md) describes the modules as pseudocode. Reading that file does not create Python.

## Scope

Two separate steps. Part 1 searches NCBI nucleotide with each `Virus` cell in the selected CSV under `output/` plus the extra term read from `output/search.txt`, and writes the first 5 accession IDs for that cell. The query text is whatever those two files contain. Part 1 does not download sequences. Part 2 reads those accession IDs and downloads each one as FASTA.

## Constitution

Engineering layout follows `constitution/CONSTITUTION.md` §I (typed OOP in `src/`) and §IV (package ownership). Those two sections are the layout rules. A later implementation is typed OOP under `src/virus_redteaming/clinical_fasta/`. `scripts/` may only assemble that object graph.

## 1. Goal

The workflow has two parts. Part 2 does not run until part 1 has written an accession file.

### Part 1: Find accession numbers

1. Read each data row of the query CSV and take the `Virus` cell.
2. Read the extra term from `output/search.txt`.
3. Search nuccore with `"{Virus}" AND {extra term}` and a sequence-length range taken from the length cutoff.
4. Keep the first 5 accessions NCBI returns, in that order.
5. Write those accessions to `output/accessions.csv`.

Part 1 calls `Bio.Entrez.esearch` only. It does not call efetch. It does not write FASTA.

### Part 2: Download FASTA by accession

1. Read the `Accession` column from `output/accessions.csv`.
2. For each distinct accession, call `Bio.Entrez.efetch` for that id.
3. Request FASTA from NCBI. Keep the record only when its sequence length is greater than the length cutoff.
4. Write one FASTA file per kept accession.

Part 2 does not call esearch. It does not compose a text query. The only identifier it sends is an accession taken from the part-1 file.

### Query text

Part 1 does not contain a query string. For each non-blank `Virus` cell it quotes that cell and AND-joins the single line read from `output/search.txt`.

Part 1 writes `output/accessions.csv` with at most 5 data rows for each `Virus` cell. Part 2 writes one FASTA file under `output/clinical_genes/` for each kept distinct accession in that file.

There is no local allowlist of accessions. The accessions are whatever esearch returns. The term must not contain an accession or an `[Accession]` qualifier.

## 2. What is downloaded

Part 2 downloads the nucleotide FASTA NCBI serves for each accession id. That is one nucleotide record per id.

## 3. Local inputs

### 3.1 Query CSV

The CSV path is `output/{filename}`. The filename is the CLI argument. The spec does not fix the cell text inside that file.

| Rule | Detail |
| --- | --- |
| Directory | Always `output/` at the repository root. |
| Default filename | genes.csv when the CLI omits the argument. |
| Rejected names | Reject /, `\`, .., a leading ., an empty name, and absolute paths. |
| Encoding | UTF-8. |
| Header | Required. One header cell must be exactly `Virus`. Other columns are ignored. |
| Rows | Each data row is processed in file order. |
| Query cell | The `Virus` cell, trimmed. A blank `Virus` cell is skipped. |
| Empty result | A valid header with no non-blank `Virus` cells is `NcbiInputError`. No Entrez call is made. |

A missing file, a path that is not a regular file, a missing `Virus` header, or a filename that escapes `output/` is `NcbiInputError`.

### 3.2 Extra term (output/search.txt)

The path is fixed. It is not a CLI argument.

| Rule | Detail |
| --- | --- |
| Encoding | UTF-8. |
| Content | Exactly one non-empty line after a single trailing newline is dropped. Strip leading and trailing whitespace on that line. |
| Extra lines | A second non-empty line is `NcbiInputError`. |
| Rejected | Empty or whitespace-only. A term containing ", [, ], (, or ). |
| Fallback | The word `or`, with spaces on both sides, splits the line into ordered alternatives. An empty alternative is `NcbiInputError`. `or` is not sent to NCBI. |

`SearchTermSource` reads the file. `SearchTermAlternatives` splits that line. `EntrezTermComposer` AND-joins one alternative with the `Virus` cell. The adapter must not substitute a hardcoded word for the file contents.

### 3.3 Term composition

For each non-blank `Virus` cell:

1. Reject the cell if it contains " (`NcbiInputError`).
2. Quote the trimmed cell as an Entrez phrase.
3. Split the search.txt line on ` or ` into ordered alternatives.
4. AND one alternative as a bare token.
5. AND the sequence-length clause from `LengthCutoff`, including `MAX_SLEN`, on that same term.

| Part | Source | Form |
| --- | --- | --- |
| Phrase | A trimmed `Virus` cell with no `[` or `]` | Quoted |
| Field query | A trimmed `Virus` cell that contains `[` or `]` | Value quoted, flag after the closing quote |
| Extra | One alternative from `output/search.txt` | Bare token, appended only to a phrase |
| Length | `LengthCutoff` | `{bp + 1}:{MAX_SLEN}[SLEN]`, appended only to a phrase |
| term | composer | `"{Virus}" AND {extra} AND {bp + 1}:{MAX_SLEN}[SLEN]`, or `"{value}"[field]` with the flag outside the quotes |

The composer must not append an accession. `human[organism] mitochondrion genome` is sent as `"human"[organism] mitochondrion genome`. `[organism]` is outside the quotes. An alternative and the `[SLEN]` clause are appended only when the cell has no field flag. `MAX_SLEN` is `LengthCutoff.MAX_SLEN` in `length.py`. The class docstring names it next to `DEFAULT_BP`. See `design/bugs/bug.NCBI.md`.

`complete genome or complete sequence` is not one Entrez query. Entrez binds `OR` more loosely than `AND`, so a single query would leave `MAX_SLEN` off the first alternative. The two alternatives are separate searches:

```text
"{Virus}" AND complete genome AND {bp + 1}:{MAX_SLEN}[SLEN]
"{Virus}" AND complete sequence AND {bp + 1}:{MAX_SLEN}[SLEN]
```

The second search runs only when the first `IdList` is empty. A field-flag cell is searched once.

## 4. Part 1 — search

Use Biopython `Bio.Entrez` against the Entrez E-utilities HTTPS endpoint. Dependency:

```text
biopython>=1.86,<2
```

Cells run in file order. Do not parallelise. For each cell, search the alternatives in order. Stop that cell when an `IdList` is non-empty. A cell with no field flag therefore gets one esearch per alternative until one returns hits.

### Search request

The `term` argument is the composer output from §3.3. It is built from the selected CSV and `output/search.txt` at run time. The client must not substitute a stored phrase.

```python
Entrez.esearch(
    db="nuccore",
    term=composed_term,
    retmax=5,
    retstart=0,
    idtype="acc",
    tool="virus_redteaming_clinical_fasta",
    email=config.email,
)
```

Pass api_key=config.api_key only when `NCBI_API_KEY` is non-empty. Do not pass api_key=None.

| Parameter | Rule |
| --- | --- |
| `db` | Always nuccore. |
| `term` | The composer output from §3.3. |
| `retmax` | 5. This is the maximum written for that `Virus` cell. |
| `retstart` | 0. Do not page. Hits after the first 5 are not requested and not written. |
| `idtype` | acc, so `IdList` contains accessions, not GI numbers. |
| `tool` | virus_redteaming_clinical_fasta. |
| `email` | Required. Passed on the call. |
| `api_key` | Optional. Never logged. |

`BiopythonEntrezClient.search` reads the handle with `Bio.Entrez.read`, closes it, and returns `IdList` in NCBI order as tuple[str, ...]. It does not drop, reorder, or choose a preferred accession.

### Search result handling

| IdList | Result |
| --- | --- |
| 1 to 5 non-empty strings | Write every item, ranks 1 through `len(IdList)`. |
| More than 5 | Not possible when retmax=5. If a response still contains more, keep the first 5 and discard the rest. |
| Empty | Skip that `Virus` cell. Print `no accessions for Virus cell: {cell}` to stderr. Continue with the next cell. |
| Every cell empty | `NcbiSearchMiss`. Do not publish `output/accessions.csv`. |
| Any item that is not a non-empty string | `NcbiSearchMiss`. Do not publish `output/accessions.csv`. |

Part 1 does not call efetch, esummary, elink, egquery, Assembly, SRA, or Datasets.

### 4.1 Accession file

Replace `output/accessions.csv` when at least one `Virus` cell returned a non-empty list. Cells with no hits are omitted and named on stderr. Write atomically: temp file in `output/`, flush, close, os.replace. On failure before replace, delete the temp file and leave the previous `output/accessions.csv` in place.

#### Header

```csv
Virus,Rank,Accession
```

One data row per kept hit. `Rank` is 1-based, in `IdList` order, and restarts at 1 for each `Virus` cell. `Virus` is the trimmed cell that was searched. `Accession` is the `IdList` string unchanged.

UTF-8. No FASTA in this file. No sequence column.

## 5. Part 2 — FASTA download

Part 2 reads `output/accessions.csv` and nothing else for its query. A missing file, a missing `Accession` header, or zero data rows is `NcbiInputError`. No Entrez call is made in those cases.

Distinct accessions are downloaded in first-seen order. A repeated accession is fetched once.

Each accession must match:

```text
^[A-Z]{1,6}_?[0-9]+(\.[0-9]+)?$
```

after stripping whitespace. Any other string is `NcbiInputError` and that id is not fetched.

One efetch per distinct accession:

### Fetch request

```python
Entrez.efetch(
    db="nuccore",
    id=accession,
    rettype="fasta",
    retmode="text",
    tool="virus_redteaming_clinical_fasta",
    email=config.email,
)
```

| Parameter | Rule |
| --- | --- |
| `db` | Always nuccore. |
| `id` | That accession only. One id per request. |
| `rettype` | fasta. |
| `retmode` | text. |
| `tool` | virus_redteaming_clinical_fasta. |
| `email` | Required. Passed on the call. |
| `api_key` | Optional. Same rule as part 1. |

Do not send term on efetch. Before every Entrez call, assign `Bio.Entrez.email`, `Bio.Entrez.tool`, and, when a key is configured, `Bio.Entrez.api_key`. Biopython reads those module attributes for the missing-email warning and for the 3-versus-10 requests-per-second limit. A key passed only as a call argument does not change the limit. When no key is configured, set `Bio.Entrez.api_key` to `None` and omit `api_key` from the call. Do not assign `Bio.Entrez.max_tries` or `Bio.Entrez.sleep_between_tries`. Calls are serial.

### Record validation

`BiopythonEntrezClient.fetch_fasta` reads the efetch handle, closes it, and returns text. `FastaFetchSource` parses that text. `Bio.SeqIO.parse` must yield exactly one record. Zero records, multiple records, or a parser exception is `NcbiRecordRejected`. The sequence must be non-empty. The length cutoff is not applied here. The output file is not opened until §5.1 accepts the length.

Identity is not a full-string match of `SeqRecord.id` to the requested accession. NCBI FASTA headers often add a version suffix or wrap the accession in a bar-separated token such as `ref|NG_007114.1|`. `AccessionIdentity` in `fasta_source.py` accepts the record when any candidate token matches the requested accession:

| Candidate | Where it comes from |
| --- | --- |
| `record.id` | The first FASTA header token, as Biopython sets it. |
| Each `\|` piece of `record.id` | Used when the token is a bar-separated id, for example `ref\|NG_007114.1\|`. |
| `record.name` | Included when Biopython sets it to a different token. |

Both the requested accession and the candidate must match `^[A-Z]{1,6}_?[0-9]+(\.[0-9]+)?$`. Their stems must be equal. If both have a version, the versions must be equal. A missing version on one side still matches. `NG_007114` matches `NG_007114.1`. `NG_007114.1` matches itself. `NG_007114.1` does not match `NG_007114.2` or `NG_007114.1.2`. The description text is ignored. A record whose tokens do not match is `NcbiRecordRejected`. The output filename stays the requested accession string. `FastaEncoder.encode` receives that accession and the record, because `record.id` may differ from the requested string.

### 5.1 Length cutoff

A record is kept only when `len(sequence) > cutoff_bp`. The default cutoff is 7000, so 7000 bp and shorter are rejected and 7001 bp and longer are kept.

The default lives in one place: `LengthCutoff.DEFAULT_BP` in `src/virus_redteaming/clinical_fasta/length.py`. `LengthCutoff.MAX_SLEN` in that same module is the upper bound of the search range. The class docstring, the `ClinicalFastaDownload` docstring, the search CLI docstring, and the download CLI docstring each name those attributes and that module. Change `DEFAULT_BP` there when the default cutoff changes. `--min-length` overrides the default for one run of `search` and of `download`. It does not edit `DEFAULT_BP`.

`LengthCutoff.accepts(sequence_length)` returns true only when `sequence_length > self.bp`. `ClinicalFastaDownload` applies this after a successful fetch. A record that fails it is skipped and not written. The run continues with the next accession. If every accession is skipped, the command raises `NcbiRecordRejected` and exits 1. A parse, identity, or empty-sequence failure still stops the run. Accessions already replaced earlier in the same run stay on disk.

### FASTA output

Write `output/clinical_genes/{accession}.fasta`. The sink creates `output/clinical_genes/` when it is missing. `BiopythonFastaEncoder` is the only type that calls `Bio.SeqIO.write`. It writes the one screened record to memory and returns text that ends with one newline. `AtomicPathFastaSink` writes that text with the same temp-file and os.replace rule as §4.1. A failed accession leaves no new temp file and does not change that destination. Accessions already replaced earlier in the same run stay on disk.

## 6. Politeness

`Bio.Entrez` owns rate limiting and retries. This adapter does not add a second retry loop.

Biopython 1.86 and later allows at most 3 requests per second without an API key and 10 with a standard API key. It retries connection failures and HTTP 5xx, at most max_tries = 3, sleeping sleep_between_tries = 15 seconds. This spec uses those published defaults.

HTTP 429 is not retried by that policy. A 429, a non-retried 4xx, an exhausted 5xx retry, a timeout, or a transport failure is `NcbiFetchError`. The same type covers an esearch body that `Bio.Entrez.read` cannot parse.

Part 1 makes one esearch per alternative until that `Virus` cell has hits. Part 2 makes one efetch per distinct accession, at most 5 per `Virus` cell. The API key comes from `NCBI_API_KEY` and is redacted from logs, exception text, and object representations.

## 7. Workflow

### Part 1

```text
output/{csv} + output/search.txt
  → OutputCsvVirusSource.read() → Virus cells
  → SearchTermSource.read() → extra term
  → SearchTermAlternatives.split(extra) → ordered alternatives
  → for each Virus cell:
        for each alternative, until one IdList is non-empty:
            EntrezTermComposer.compose(virus, alternative, cutoff) → term
            NucleotideSearcher.search(term) → up to 5 accessions
        skip a cell whose every IdList is empty
  → AccessionTableSink.write(...) → output/accessions.csv
```

### Part 2

```text
output/accessions.csv
  → AccessionTableSource.read() → distinct accessions in first-seen order
  → LengthCutoff (DEFAULT_BP, or --min-length for this run)
  → for each accession:
        NucleotideFetch.fetch_fasta(accession) → text
        FastaRecordSource.fetch(accession) → SeqRecord
        skip when LengthCutoff.accepts(len(sequence)) is false
        FastaEncoder.encode(accession, record) → FastaRecord
        FastaSink.write(record) → output/clinical_genes/{accession}.fasta
```

`AccessionSearch` is the only type that sequences part 1. `ClinicalFastaDownload` is the only type that sequences part 2. Neither opens sockets itself. Part 1 does not write FASTA. Part 2 does not search.

## 8. Types

Package: `src/virus_redteaming/clinical_fasta/`. Protocols live in protocols.py. Errors live in errors.py. The entrypoint is `clinical_fasta/__main__.py`. The top-level `virus_redteaming/__main__.py` remains the catalogue entrypoint.

| Type | Module | Responsibility |
| --- | --- | --- |
| `AccessionHit` | `models.py` | Frozen value: `Virus` cell, rank, accession. |
| `FastaRecord` | `models.py` | Frozen value: accession plus FASTA text. |
| `NcbiEntrezConfig` | `config.py` | Frozen value: email, tool, optional API key. Rejects a missing email or an email containing whitespace. Redacts the key. |
| `OutputCsvPath` | `paths.py` | Resolves a filename to `output/{filename}`. Rejects traversal and invalid filenames. |
| `VirusQuerySource` | `protocols.py` | read() -> tuple[str, ...]. |
| `SearchTermSource` | `protocols.py` | read() -> str. |
| `NucleotideSearcher` | `protocols.py` | search(term: str) -> tuple[str, ...]. |
| `AccessionTableSink` | `protocols.py` | write(hits: Sequence[`AccessionHit`]) -> Path. |
| `AccessionTableSource` | `protocols.py` | read() -> tuple[str, ...]. Distinct accessions. |
| `NucleotideFetch` | `protocols.py` | fetch_fasta(accession: str) -> str. The handle is already closed. |
| `FastaRecordSource` | `protocols.py` | fetch(accession: str) -> `SeqRecord`. |
| `FastaEncoder` | `protocols.py` | encode(accession: str, record: `SeqRecord`) -> `FastaRecord`. |
| `FastaSink` | `protocols.py` | write(record: `FastaRecord`) -> Path. |
| `OutputCsvVirusSource` | `csv_source.py` | Yields trimmed `Virus` cells. Skips blanks. |
| `OutputSearchTermSource` | `search_term.py` | Reads the injected path. The CLI passes `output/search.txt`. |
| `SearchTermAlternatives` | `search_term.py` | Splits the search.txt line on ` or ` into ordered fallback phrases. |
| `EntrezTermComposer` | `term.py` | Builds "{virus}" AND {extra} AND the `[SLEN]` clause. |
| `BiopythonEntrezClient` | `biopython_entrez.py` | esearch for part 1 and efetch FASTA for part 2. |
| `AccessionList` | `accession_list.py` | Applies the §4 size and emptiness rules. |
| `AtomicAccessionTableSink` | `accession_sink.py` | Atomically writes the injected destination. The CLI passes `output/accessions.csv`. |
| `AccessionCsvSource` | `accession_source.py` | Reads the injected path and validates accession syntax. The CLI passes `output/accessions.csv`. |
| `LengthCutoff` | `length.py` | Default cutoff `DEFAULT_BP = 7000`. Upper search bound `MAX_SLEN`. `accepts` is true only when the sequence is longer than `bp`. Docstring names both attributes in this module. |
| `AccessionIdentity` | `fasta_source.py` | Matches a requested accession to `record.id`, its `\|` tokens, and `record.name`, allowing a version suffix. |
| `FastaFetchSource` | `fasta_source.py` | Parses text from `NucleotideFetch` into exactly one FASTA record that `AccessionIdentity` accepts. |
| `BiopythonFastaEncoder` | `fasta_encoder.py` | `Bio.SeqIO.write` of that one record. The accession argument is stored, not `record.id`. |
| `AtomicPathFastaSink` | `sink.py` | Atomically writes `{directory}/{accession}.fasta`. The CLI passes `output/clinical_genes`. |
| `AccessionSearch` | `search_workflow.py` | Part 1. run() -> Path. |
| `ClinicalFastaDownload` | `download_workflow.py` | Part 2. run() -> tuple[Path, ...]. Its docstring names `LengthCutoff.DEFAULT_BP` in `length.py` as the default cutoff and says that `--min-length` overrides it for one run. |

### Protocol signatures

```python
class NucleotideSearcher(Protocol):
    def search(self, term: str) -> tuple[str, ...]: ...


class NucleotideFetch(Protocol):
    def fetch_fasta(self, accession: str) -> str: ...


class FastaRecordSource(Protocol):
    def fetch(self, accession: str) -> SeqRecord: ...


class FastaEncoder(Protocol):
    def encode(self, accession: str, record: SeqRecord) -> FastaRecord: ...
```

`BiopythonEntrezClient` receives `NcbiEntrezConfig` through `__init__`. Unit tests pass fakes for these protocols and do not call NCBI.

## 9. CLI

`python -m virus_redteaming.clinical_fasta` takes a subcommand.

### Part 1: Search

```bash
python -m virus_redteaming.clinical_fasta search
python -m virus_redteaming.clinical_fasta search {filename}
python -m virus_redteaming.clinical_fasta search {filename} --min-length 7000
```

`search` with no argument reads `output/genes.csv`. `search {filename}` reads `output/{filename}`. Both read the extra term from `output/search.txt` and search with `"{Virus}" AND {extra} AND {bp + 1}:{MAX_SLEN}[SLEN]`. Neither command contains a stored query phrase. `--min-length` overrides `LengthCutoff.DEFAULT_BP` for this search. Each `Virus` cell keeps at most 5 accessions. A cell with no hits is omitted and printed to stderr as `no accessions for Virus cell: {cell}`. The command writes `output/accessions.csv` when at least one cell has hits and prints that path to stdout. Exit 1 when any cell has no hits, including when every cell has no hits. Exit 0 when every cell returns at least one accession.

### Part 2: Download

```bash
python -m virus_redteaming.clinical_fasta download
python -m virus_redteaming.clinical_fasta download --min-length 7000
```

Reads `output/accessions.csv`. Skips a record whose sequence length is not greater than the cutoff and continues. The omitted flag uses `LengthCutoff.DEFAULT_BP` (7000) from `length.py`. `--min-length` is an integer of 0 or greater and replaces that default for this run. A missing value, a non-integer, or a negative value is a usage error and exits 2. One FASTA path per kept accession is printed, one per line. Exit 0 when at least one accession is written. Exit 1 when every accession is skipped for length.

### Shared rules

`NCBI_EMAIL` is required. A missing email, or an email containing whitespace, is a usage error before any request.

`NCBI_API_KEY` is optional. An empty value is omitted from Entrez calls.

A bad argument or `NcbiConfigError` prints to stderr and exits 2.

Any other package error prints to stderr and exits 1.

`download` takes no query filename. Its only option is `--min-length`.

### End to end

```bash
python -m virus_redteaming.clinical_fasta run
python -m virus_redteaming.clinical_fasta run {filename}
python -m virus_redteaming.clinical_fasta run {filename} --min-length 7000
```

`run` with no argument starts at `output/genes.csv`. It searches, downloads the accessions that search wrote, then parses. A `Virus` cell with no hits is printed to stderr and omitted from `output/accessions.csv`. Download and parse still run for the cells that have hits. Exit 1 when any cell has no hits or when search, download, or parse raises. Exit 0 when every cell returns at least one accession and download and parse both finish. When every cell has no hits, search raises `NcbiSearchMiss` and download and parse do not run.

## 10. Errors

| Condition | Type |
| --- | --- |
| CSV missing, not a file, escapes `output/`, missing `Virus` header, no non-blank `Virus` cells, `Virus` cell contains ", or search.txt missing, empty, multi-line, or containing "[]\() | `NcbiInputError` |
| Part 2 accession file missing, missing `Accession`, empty, or containing an id that fails the accession pattern | `NcbiInputError` |
| Email missing or containing whitespace | `NcbiConfigError` |
| every `Virus` cell returns no accessions, or an `IdList` item is not a non-empty string | `NcbiSearchMiss` |
| Transport failure, non-success status, exhausted Biopython retry, or an unreadable esearch body | `NcbiFetchError` |
| FASTA parse fails, the record count is not one, no header token matches the requested accession under §5, the sequence is empty, or every fetched accession is shorter than or equal to the cutoff | `NcbiRecordRejected` |
| `Accession`-table or FASTA atomic persistence fails | `FastaWriteError` |

All of these are subclasses of one package error base. Do not raise bare Exception. Exception messages must not include the API key. A part-1 failure does not publish a new `output/accessions.csv`. A part-2 failure does not leave a temp FASTA for the accession that failed.

## 11. Tests

### Unit tests (no network)

| Test | Asserts |
| --- | --- |
| `test_csv_path_resolves_under_output` | A bare filename resolves under `output/`. ../secrets.csv, /tmp/x.csv, and a/b.csv raise `NcbiInputError`. |
| `test_csv_reads_virus_column_in_order` | A non-blank cell, a blank cell, then another non-blank cell yield those two trimmed cells in order. |
| `test_csv_rejects_missing_virus_header` | A header without `Virus` raises `NcbiInputError`. |
| `test_csv_rejects_all_blank_virus_cells` | Header only, or only blank `Virus` cells, raises `NcbiInputError`. |
| `test_search_txt_reads_the_single_line` | One non-empty line, after dropping a trailing newline and surrounding whitespace, is the extra term. |
| `test_search_txt_rejects_empty_and_multiple_terms` | Empty, whitespace-only, and two non-empty lines raise `NcbiInputError`. |
| `test_term_composer_quotes_virus_and_ands_extra` | A cell with no brackets returns `"{Virus}" AND {extra} AND {bp + 1}:{MAX_SLEN}[SLEN]`, with no accession and no `[Accession]`. |
| `test_search_retries_the_next_alternative_with_the_length_max` | `complete genome or complete sequence` searches `complete genome` first. An empty `IdList` searches `complete sequence`. Both terms contain `{bp + 1}:{MAX_SLEN}[SLEN]`. A hit on the first alternative does not send the second. |
| `test_term_composer_sends_field_query_unquoted` | `human[organism] mitochondrion genome` is sent as `"human"[organism] mitochondrion genome`. `[organism]` is outside the quotes, and `AND gene` is not appended. |
| `test_field_query_keeps_all_five_hits` | That field query is the term sent to search. All five returned accessions are written. |
| `test_download_writes_all_five_mitochondrion_genomes` | The five accessions from that query, each longer than the cutoff, are all written. |
| `test_term_composer_rejects_embedded_quotes` | A `Virus` cell containing `"` raises `NcbiInputError`. |
| `test_search_keeps_first_5_in_order` | An 8-id response writes ranks 1–5 in response order. A 3-id response writes ranks 1–3. |
| `test_search_miss_does_not_publish_accession_file` | One empty `IdList` is omitted, reported on the result, and the other cell is written. When every cell is empty, `NcbiSearchMiss` is raised and an existing `output/accessions.csv` is not replaced. |
| `test_search_does_not_call_efetch` | Part 1 calls esearch with retmax=5, retstart=0, and idtype=acc. It does not call efetch. |
| `test_download_fetches_each_distinct_accession_as_fasta` | Accessions A1, A2, A1 produce two `fetch_fasta` calls, ids A1 then A2. The client closes the handle before returning text, uses rettype=fasta and retmode=text, and sends no term. |
| `test_download_rejects_malformed_accession` | An id outside the §5 pattern raises `NcbiInputError` and does not call efetch. |
| `test_fasta_source_accepts_one_matching_record` | One FASTA record whose id equals the requested accession is returned from text supplied by a `NucleotideFetch` fake. |
| `test_fasta_identity_accepts_version_and_bar_token` | Requested `NG_007114` matches `NG_007114.1` and `ref\|NG_007114.1\|`. `NG_007114.1` does not match `NG_007114.2` or `NG_007114.1.2`. |
| `test_fasta_source_rejects_wrong_count_or_id` | Zero records, two records, a mismatched accession, or an empty sequence raises `NcbiRecordRejected`. |
| `test_length_cutoff_default_is_7000_and_is_exclusive` | `LengthCutoff.DEFAULT_BP` is 7000. `MAX_SLEN` is the search upper bound. Length 7000 is rejected. Length 7001 is accepted. The SLEN clause is `7001:{MAX_SLEN}[SLEN]`. |
| `test_download_min_length_overrides_default` | `--min-length 10000` skips a 9000 bp record, writes a later longer record, and does not change `LengthCutoff.DEFAULT_BP`. |
| `test_download_skips_short_records_and_fails_when_none_remain` | A short record followed by a long one writes only the long one. A run where every record is short raises `NcbiRecordRejected` and writes nothing. |
| `test_entrez_client_omits_unset_api_key` | With no key, neither call receives api_key. With a key, that key is passed on both. |
| `test_sink_replaces_atomically_and_removes_temp_on_failure` | Success leaves no temporary file. A failure before os.replace deletes the temporary file and leaves an existing destination unchanged. |
| `test_errors_and_logs_redact_api_key` | The API key does not appear in exception text, logs, or object representation. |

### Opt-in integration test

An integration test that calls NCBI is opt-in only. It requires both `NCBI_LIVE_TEST=1` and `NCBI_EMAIL`, and is marked network. It reads the selected CSV and `output/search.txt`, sends only the term `EntrezTermComposer` builds from those files, and uses retmax=5. It must not embed a query string. It then FASTA-fetches only accessions written by that search and keeps a record only when its length is greater than the cutoff. Setting an email must not make normal CI use the network.

## 12. Manual check

With `NCBI_EMAIL` set, put the query phrases in the `Virus` column of a CSV under `output/` and put the extra term on the single line of `output/search.txt`. Then run:

```bash
python -m virus_redteaming.clinical_fasta search {filename}
python -m virus_redteaming.clinical_fasta download
```

For a successful run:

1. The first command writes `output/accessions.csv` with header `Virus,Rank,Accession` and between 1 and 5 data rows for each non-blank `Virus` cell. It prints the CSV path to stdout.
2. The second command writes one FASTA file per kept accession to `output/clinical_genes/{accession}.fasta` when that sequence is longer than `LengthCutoff.DEFAULT_BP` (7000) in `length.py`. A sequence of 7000 bp or shorter is skipped. Repeated accessions are downloaded once. It prints each kept FASTA path on a separate line. `python -m virus_redteaming.clinical_fasta download --min-length N` uses N instead of `DEFAULT_BP` for that run.
3. Exit status is `0` when at least one accession is written. Exit status is `1` when every accession is skipped for length.