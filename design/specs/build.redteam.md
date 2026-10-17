# build.redteam.md

**Status:** accepted  
**Companion spec:** [spec.redteam.md](spec.redteam.md)  
**Implements:** parse `misc208.pdf` printed pages **27–42** → `output/viruses.csv`  
**Scope:** clinical genes and genomes are not pathogen work (ADR 0004); pathogen genomes remain prohibited.

This is the build record for the code that exists under `src/virus_redteaming/catalogue/` and `src/virus_redteaming/__main__.py`. Each module is described as pseudocode. Remedies below are the bugs from the first extractor (page 27 → EOF, CSV written to a naked `viruses.csv`).

## 0. Bugs this build remediates

| Bug | First build | Remedy |
| --- | --- | --- |
| Page range | `for page in pdf.pages[26:]` (27 to last page, including Annex 1) | Inclusive window **27–42**. Halt before page 43. |
| Annex 1 | Parser hoped to see an `Annex 1` **table row**. Annex 1 is a **page title**, not a table cell, so the first build could keep reading. | `VirusSectionPageSelector` never includes a page whose text has HSE + Annex 1 title. Combined with `printed_page > 42` → `HALT` + `break`. |
| CLI artefact | `--out viruses.csv` (cwd, no directory) | Default `CatalogueOutputPath` → **`output/viruses.csv`**. Create `output/` on write. |
| Spec vs code | Code was written against “page 27 to end” | Spec §5 now matches the selector. This file is the build that the spec describes. |

## 1. How the parse stops on page 42

Printed page N is PDF index `N - 1`. Page 42 is the last Togaviridae / alphavirus table. Page 43 opens with:

```text
Health and Safety Executive
Annex 1: Biological agents
which may be used at less
than the minimum
containment conditions
```

Every catalogue page also says `Health and Safety Executive`. That string alone is **not** a stop. The stop is the **pair** (HSE header + Annex 1 title) **or** any printed page outside 27–42.

```
open pdf
for printed_page from 1 to page_count:
    decision ← selector.decide(printed_page, page_text)
    if decision is HALT:
        if printed_page < 27:
            continue          # skip bacteria/fungi/prion pages
        else:
            break             # page 43+, or Annex 1 title: do not extract
    extract every table cell on this page into TableRow(printed_page)
parser.parse(rows)            # sticky Family/Genus; ignore chrome
writer.write(output/viruses.csv)
```

`HALT` on page 43 happens even if Annex 1 detection failed, because `PrintedPageWindow.contains(43)` is false. Annex detection is the second latch if page numbers ever drift.

No type after the extractor is allowed to “keep going until EOF”.

## 2. SOLID map

| Principle | How |
| --- | --- |
| S | Window, halt policy, selector, PDF adapter, classifier, parser, path, CSV writer, CLI are separate types |
| O | New halt rules implement `PageHaltPolicy`; extractor does not grow `if` ladders |
| L | Fakes in tests honour `TableExtractor` / `RecordSink` / `PageHaltPolicy` |
| I | Extractor does not depend on CSV; writer does not depend on PDF |
| D | `ParseApprovedVirusList` depends on Protocols; pdfplumber lives only in `PdfPlumberTableExtractor` |

## 3. Pseudocode per module

### 3.1 `catalogue/page_window.py`

```
PrintedPageWindow(start=27, end=42)
    contains(n) → start ≤ n ≤ end

AnnexTitleHaltPolicy
    should_halt(text) →
        "health and safety executive" in text
        AND "annex 1: biological agents which may be used at less than the minimum containment conditions" in text

VirusSectionPageSelector(window, annex_halt)
    decide(printed_page, text) →
        HALT if not window.contains(printed_page)
        HALT if annex_halt.should_halt(text)
        else INCLUDE
```

### 3.2 `catalogue/pdf_tables.py` — `PdfPlumberTableExtractor`

```
extract(pdf_path):
    rows ← []
    open pdfplumber(pdf_path)
    for index, page in pages:
        printed ← index + 1
        if selector.decide(printed, page.text) is HALT:
            if printed < window.start: continue
            else break
        for table in page.tables:
            for raw_row in table:
                rows.append(TableRow(agent, hg, notes, printed_page=printed))
    return rows
```

### 3.3 `catalogue/row_classifier.py` — `RowClassifier`

```
classify(row):
    IGNORE  if empty or page chrome (Biological agent / Human pathogen / …)
    FAMILY_AND_GENUS | FAMILY | GENUS  if column 1 matches those headers
    AGENT   if column 1 is a name and column 2 matches /^[1-4]\*?$/
    else IGNORE
```

Annex 1 is **not** the primary stop here. If a leaked cell starts with `Annex 1`, still treat as end (defence in depth).

### 3.4 `catalogue/parser.py` — `ApprovedVirusListParser`

```
parse(rows):
    family, genus ← "", ""
    in_section ← false
    for row in rows:
        kind ← classifier.classify(row)
        if SECTION_START "Viruses": in_section ← true
        if not in_section: continue
        if FAMILY: family ← name; genus ← ""
        if GENUS: genus ← name
        if FAMILY_AND_GENUS: set both
        if AGENT: emit VirusRecord(family, genus, collapsed name, hg, § or "")
    fail if Viruses heading never seen
```

### 3.5 `catalogue/text.py`

```
collapse_whitespace: newlines → spaces, squeeze, rejoin wrapped "spring–\\nsummer"
row_has_schedule_5: any cell contains "§"
```

### 3.6 `catalogue/paths.py` — `CatalogueSourcePath` / `CatalogueOutputPath`

```
CatalogueSourcePath
    directory_name = "docs"
    filename = "misc208.pdf"
    resolve(root=cwd) → root / "docs" / "misc208.pdf"

CatalogueOutputPath
    directory_name = "output"
    filename = "viruses.csv"
    resolve(root=cwd) → root / "output" / "viruses.csv"
```

### 3.7 `catalogue/csv_sink.py` — `LongFormatCsvWriter`

```
write(records):
    mkdir parent of destination
    header ← Family, Genus, Virus, Human pathogen hazard group, schedule 5
    one CSV row per VirusRecord
```

### 3.8 `catalogue/workflow.py` — `ParseApprovedVirusList`

```
run(pdf_path):
    rows ← extractor.extract(pdf_path)
    records ← parser.parse(rows)
    sink.write(records)
    return len(records)
```

No page numbers, no CSV layout, no pdfplumber.

### 3.9 `__main__.py` (CLI only)

```
parse-viruses [--pdf PATH] [--out PATH]
    default --pdf ← CatalogueSourcePath().resolve()   # docs/misc208.pdf
    default --out ← CatalogueOutputPath().resolve()   # output/viruses.csv
    wire PdfPlumberTableExtractor + ApprovedVirusListParser + LongFormatCsvWriter
    run workflow
```

No parse rules in the CLI.

### 3.10 `catalogue/models.py`

```
TableRow(agent, hazard_group, notes, printed_page=0)
VirusRecord(family, genus, virus, hazard_group, schedule_5)
```

## 4. Default command

```bash
python -m virus_redteaming parse-viruses
```

Reads **`docs/misc208.pdf`**. Writes **`output/viruses.csv`**. Generated CSVs stay out of git; `output/.gitkeep` keeps the directory.

## 5. Tests that lock the stop

- `test_window_is_printed_pages_27_through_42_inclusive`  
- `test_selector_includes_27_and_42_and_halts_43`  
- `test_hse_header_alone_does_not_halt_a_virus_table_page`  
- integration `test_extractor_stops_on_printed_page_42` (max `printed_page == 42`, no `annex 1:` in agents)
