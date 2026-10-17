# build.schedule5.md

**Status:** accepted  
**Companion spec:** [spec.schedule5.md](spec.schedule5.md)  
**Target:** annotate `output/viruses.csv` so **Schedule 5** is `1` or `0`

## Execution rule

Reading or editing this file does **not** create Python.

A request to **run this build** (this document named, or “run `build.schedule5.md`”) **does** create the modules and the Pytest files in §2 and §4, then runs:

```bash
python3 -m pytest tests/unit/catalogue/test_schedule5_loader.py tests/unit/catalogue/test_schedule5_interactor.py tests/unit/catalogue/test_schedule5_annotator.py tests/integration/test_schedule5_annotate.py -q
```

Do not fold the annotator into `ApprovedVirusListParser`. Do not import pdfplumber from these modules. Do not join the ICTV CSV into `viruses.csv`.

## 0. Locked inventory (this tree, 2026-10-17)

| File | What is counted | Count |
| --- | --- | --- |
| `docs/ICTV_RNA_virus_species_MSL41.csv` | data rows (not header) | **7230** |
| `output/viruses.csv` | data rows (not header) | **232** |
| `docs/schedule5.md` | markdown `- ` bullets | **46** |

The ICTV file is an inventory lock only.

### 0.1 Accounting identity

After annotation:

```
len(updated data rows) = 232 = len(original data rows)

46 = |matched schedule-5 names| + |unmatched names|
```

One schedule-5 name may flag several catalogue rows (Ebola, Polio, LCMV). Therefore:

```
count(Schedule 5 == "1") ≥ |matched schedule-5 names|
count(Schedule 5 == "1") + count(Schedule 5 == "0") = 232
```

`count(Schedule 5 == "1")` is not required to equal 46.

### 0.2 Identity except Schedule 5

For every row index `i` in `0 .. 231`, Family, Genus, Virus, and Human pathogen hazard group are equal before and after. Virus strings are not rewritten to the markdown wording. Only Schedule 5 changes, from empty or `§` to `"1"` or `"0"`. Row order is unchanged.

## 1. Modules created when this build is run

| Module | Type |
| --- | --- |
| `src/virus_redteaming/catalogue/schedule5_source.py` | `Schedule5NameSource` (Protocol), `MarkdownBulletNameSource` |
| `src/virus_redteaming/catalogue/schedule5_match.py` | `VirusNameNormaliser`, `VirusNameInteractor` |
| `src/virus_redteaming/catalogue/schedule5_annotate.py` | `CatalogueRow`, `AnnotationResult`, `CatalogueCsvReader`, `Schedule5CsvWriter`, `UnmatchedNameSink`, `Schedule5CsvAnnotator`, `AnnotateSchedule5` |
| `src/virus_redteaming/__main__.py` | subcommand `annotate-schedule-5` only; no match rules |
| `tests/unit/catalogue/test_schedule5_loader.py` | §4.2 |
| `tests/unit/catalogue/test_schedule5_interactor.py` | §4.3 |
| `tests/unit/catalogue/test_schedule5_annotator.py` | §4.4 |
| `tests/integration/test_schedule5_annotate.py` | §4.5 |

Constants, used by tests and by the CLI defaults:

```
ICTV_RNA_ROW_COUNT = 7230
VIRUSES_CSV_ROW_COUNT = 232
SCHEDULE5_NAME_COUNT = 46
REPO_ROOT = Path(__file__).resolve().parents[3]   # tests only; package code takes paths
VIRUSES_CSV = REPO_ROOT / "output" / "viruses.csv"
SCHEDULE5_MD = REPO_ROOT / "docs" / "schedule5.md"
ICTV_CSV = REPO_ROOT / "docs" / "ICTV_RNA_virus_species_MSL41.csv"
UNMATCHED_NAME = "schedule5_unmatched.txt"
```

`parents[3]` is correct for a file under `tests/unit/catalogue/` or `tests/integration/`. Put the four path constants in `tests/conftest.py` so unit and integration tests share one definition. Do not invent `load_46` or `load_232` as free functions; the fixtures in §4.1 are the only loaders.

## 2. Pseudocode

### 2.1 `MarkdownBulletNameSource`

```
load(path) -> tuple[str, ...]:
    names ← []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("- "):
            names.append(line[2:].strip())
    return tuple(names)
```

The loader does not assert 46. The tests do.

### 2.2 `VirusNameNormaliser`

```
normalise(text) -> str:
    NFKC
    casefold
    strip combining marks (sabiá → sabia)
    replace "/", "_", "–", "—" with "-"
    squeeze whitespace
    return text
```

Do not strip the word `virus`.

### 2.3 `VirusNameInteractor`

Constructor takes a `VirusNameNormaliser`. Synonym pairs are the table in spec.schedule5.md §3.2, stored on the interactor, compared after `normalise` on both sides.

```
interacts(virus_cell, schedule_names) -> bool:
    return bool(matched_names(virus_cell, schedule_names))

matched_names(virus_cell, schedule_names) -> frozenset[str]:
    hits ← empty set
    n ← normalise(virus_cell)
    if n contains "spp." or n startswith "other ":
        return empty          # catch-all rows do not inherit Schedule 5
    for name in schedule_names:
        s ← normalise(name)
        if n == s: hits.add(name)
        else if len(s) ≥ 6 and (s in n or n in s): hits.add(name)
        else if an alias span in virus_cell ("also known as" / "formerly known as" / "formerly") normalises equal to s: hits.add(name)
        else if (normalise(name), n) is a synonym pair: hits.add(name)
        else if name == "Ebola virus" and "ebola" in n: hits.add(name)
        else if name == "Polio virus" and n startswith "poliovirus": hits.add(name)
        else if name == "SARS Coronavirus" and "sars-cov-1" in n and "sars-cov-2" not in n: hits.add(name)
        else if name == "Influenza viruses (pandemic strains)" and n contains "pandemic": hits.add(name)
        else if name startswith "Tick-borne encephalitis virus" and ("far eastern tick-borne" in n or "russian spring" in n): hits.add(name)
    return frozenset(hits)
```

Family and Genus are not arguments. Influenza B, C, and D do not match the pandemic-strain bullet unless the Virus cell itself contains `pandemic`.

### 2.4 Rows, reader, writer

```
CatalogueRow: frozen dataclass
    family, genus, virus, hazard_group, schedule_5: str

CatalogueCsvReader.read(path) -> tuple[CatalogueRow, ...]:
    csv.DictReader
    accept header "schedule 5" or "Schedule 5" for the last field
    one CatalogueRow per data row

Schedule5CsvWriter.write(path, rows):
    mkdir parent
    header exactly:
        Family, Genus, Virus, Human pathogen hazard group, Schedule 5
    one row per CatalogueRow, schedule_5 already "1" or "0"

UnmatchedNameSink.write(path, names):
    one original markdown name per line, sorted, trailing newline
    empty file (zero bytes or a single empty write) when names is empty
```

### 2.5 `Schedule5CsvAnnotator`

```
AnnotationResult:
    rows: tuple[CatalogueRow, ...]
    matched_names: frozenset[str]
    unmatched_names: tuple[str, ...]    # original spelling, stable sorted

annotate(original_rows, schedule_names) -> AnnotationResult:
    updated ← []
    used ← empty set
    for row in original_rows:
        hits ← interactor.matched_names(row.virus, schedule_names)
        used |= hits
        updated.append(replace(row, schedule_5="1" if hits else "0"))
    unmatched ← tuple(sorted(name for name in schedule_names if name not in used))
    return AnnotationResult(tuple(updated), frozenset(used), unmatched)
```

`used` is returned as `matched_names`. Callers must not refer to a name that this method does not return.

### 2.6 `AnnotateSchedule5`

```
__init__(source, reader, annotator, writer, unmatched_sink)

run(list_path, csv_path, unmatched_path) -> AnnotationResult:
    names ← source.load(list_path)
    original ← reader.read(csv_path)
    result ← annotator.annotate(original, names)
    unmatched_sink.write(unmatched_path, result.unmatched_names)
    writer.write(csv_path, result.rows)
    return result
```

Paths are arguments. The workflow does not hard-code `output/viruses.csv`, so tests pass `tmp_path` copies. It does not assert the 232/46 counts; tests do.

CLI, in `__main__.py` only:

```
annotate-schedule-5
    --list default docs/schedule5.md   (CatalogueSource-style path under cwd)
    --csv  default output/viruses.csv
    unmatched path = csv_path.parent / "schedule5_unmatched.txt"
    wire the five collaborators and call run
```

## 3. Invariants the tests lock

1. `MarkdownBulletNameSource.load(SCHEDULE5_MD)` has length 46 and no duplicate strings.
2. `CatalogueCsvReader.read(VIRUSES_CSV)` has length 232 before annotation.
3. ICTV data-row count is 7230. No other assertion touches that file.
4. `len(matched_names) + len(unmatched_names) == 46`, the two sets partition the 46 names, and they are disjoint.
5. Virus, Family, Genus, and hazard group sequences are identical before and after.
6. Every updated `schedule_5` is `"0"` or `"1"`, and the two counts sum to 232.
7. Every name in `matched_names` interacts with at least one row whose `schedule_5` is `"1"`. No unmatched name interacts with any flagged row.
8. Spot checks (Virus → Schedule 5): Andes `0`, Dengue `1`, Louping ill `1`, Yellow fever `1`, Zika `0`, Guanarito `1`, Zaire ebolavirus `1`, Adenoviridae spp. known to be pathogenic in humans `0`. SARS-CoV-2 is `0`. The SARS-CoV-1 row is `1`.
9. Integration copies `output/viruses.csv` into `tmp_path` and annotates the copy. It does not write the repo `output/viruses.csv`.

## 4. Pytest written when this build is run

### 4.1 Shared fixtures (`tests/conftest.py`)

```
def schedule5_names() -> tuple[str, ...]:
    return MarkdownBulletNameSource().load(SCHEDULE5_MD)

def catalogue_rows() -> tuple[CatalogueRow, ...]:
    return CatalogueCsvReader().read(VIRUSES_CSV)

def interactor() -> VirusNameInteractor:
    return VirusNameInteractor(VirusNameNormaliser())

def annotator(interactor) -> Schedule5CsvAnnotator:
    return Schedule5CsvAnnotator(interactor)
```

`count_csv_data_rows(path)` lives in `tests/conftest.py`: `len(list(csv.reader(path.open()))) - 1`. Tests call that function. They do not call undefined helpers.

### 4.2 `tests/unit/catalogue/test_schedule5_loader.py`

- `test_schedule5_md_has_46_bullets`: `len(schedule5_names) == 46` and `len(set(schedule5_names)) == 46`.
- `test_viruses_csv_has_232_data_rows`: `len(catalogue_rows) == 232`.
- `test_ictv_msl41_has_7230_data_rows`: `count_csv_data_rows(ICTV_CSV) == 7230`.

### 4.3 `tests/unit/catalogue/test_schedule5_interactor.py`

Build rows with `annotator.annotate(catalogue_rows, schedule5_names)` once per test (or a fixture `annotation_result`).

- `test_schedule5_names_partition_into_matched_and_unmatched`: `len(matched) + len(unmatched) == 46`, `set(schedule5_names) == matched | set(unmatched)`, disjoint.
- `test_sars_cov_2_is_not_schedule_5` and `test_sars_cov_1_is_schedule_5`: find the Virus cells containing `SARS-CoV-2` and `SARS-CoV-1`.
- `test_spot_checks`: the eight Virus → `0`/`1` pairs in §3.8, keyed by the Virus field of `annotation_result.rows`.

### 4.4 `tests/unit/catalogue/test_schedule5_annotator.py`

- `test_virus_column_unchanged`: Virus sequence of `catalogue_rows` equals Virus sequence of `annotation_result.rows`.
- `test_only_schedule_5_field_changes`: zip original and updated; Family, Genus, Virus, hazard group equal; updated schedule_5 in `{"0", "1"}`; lengths both 232.
- `test_each_matched_schedule5_name_has_a_flagged_virus_row`: for each name in `matched_names`, some flagged row (`schedule_5 == "1"`) satisfies `interactor.interacts(row.virus, (name,))`. For each unmatched name, no flagged row interacts.
- `test_schedule5_column_is_binary_and_covers_all_rows`: ones + zeros == 232, no other values.

### 4.5 `tests/integration/test_schedule5_annotate.py`

Fixture `tmp_catalogue_copy(tmp_path)` copies `VIRUSES_CSV` to `tmp_path / "viruses.csv"` and returns that path. Unmatched path is `tmp_path / "schedule5_unmatched.txt"`.

- `test_inventory_counts_on_disk`: 232, 46, and 7230 against the repo paths. Does not call `AnnotateSchedule5`.
- `test_annotate_preserves_row_count_and_virus_names`: snapshot the tmp CSV, `AnnotateSchedule5(...).run(SCHEDULE5_MD, tmp_csv, unmatched_path)`, re-read. Lengths 232. Virus sequences equal. The four stable fields equal on each zipped pair. Updated schedule_5 in `{"0", "1"}`. Repo `output/viruses.csv` byte-identical to its pre-test contents (read both, or hash before and after).
- `test_schedule5_list_is_fully_accounted_for`: after `run` on the tmp copy, `len(matched_names) + len(unmatched file lines) == 46` and the sets partition `schedule5_names`. Empty unmatched file means zero lines, not one blank line.

## 5. What a run of this build does not do

- Does not parse `misc208.pdf`.
- Does not join the 7230 ICTV rows into the 232-row catalogue.
- Does not add CSV rows for unmatched schedule-5 names.
- Does not overwrite `output/viruses.csv` from the test suite. The CLI, when the user runs `annotate-schedule-5`, is what writes `output/viruses.csv` and `output/schedule5_unmatched.txt`.

## 6. Command after the build has been run

```bash
python -m virus_redteaming annotate-schedule-5
```

Defaults: `--list docs/schedule5.md`, `--csv output/viruses.csv`. Unmatched names go to `output/schedule5_unmatched.txt`.
