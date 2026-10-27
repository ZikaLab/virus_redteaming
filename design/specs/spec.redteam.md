# spec.redteam.md

**Status:** accepted  
**Source document:** HSE/ACDP *The Approved List of biological agents* (`misc208.pdf`, sixth edition, 2026)  
**Scope:** extract the **Viruses** catalogue from **printed pages 27–42 inclusive** into long-format CSV  
**Build:** [build.redteam.md](build.redteam.md) describes the implemented types as pseudocode.

## 1. Goal

Parse `misc208.pdf` from **printed page 27 through printed page 42**. Locate the table heading **Viruses**. Emit one CSV row per listed virus (or “spp. known to be pathogenic…” catch-all) with:

| Column | Source |
| --- | --- |
| Family | Last seen `Family …` header in column 1 |
| Genus | Last seen `Genus …` header in column 1 (blank if the family has no genus row) |
| Virus | `Biological agent` cell, newlines collapsed to spaces |
| Human pathogen hazard group | `Human pathogen hazard group` cell, including a trailing `*` when the PDF prints one (`3*`) |
| Schedule 5 | Filled later by [spec.schedule5.md](spec.schedule5.md): `1` if Virus interacts with `docs/schedule5.md`, else `0`. The PDF parse leaves this cell empty; it does not infer membership from `§` or `*`. |

Header line (exact names):

```text
Family, Genus, Virus, Human pathogen hazard group, "schedule 5"
```

## 2. PDF layout (printed pages 27–42)

Each page is a three-column table:

1. Biological agent  
2. Human pathogen hazard group  
3. Taxonomy / notes  

Row kinds in column 1:

- Section title: `Viruses` (start).  
- Taxonomy headers: `Family <Name>` and/or `Genus <Name>` in the same cell or adjacent cells, hazard group empty.  
- Agent rows: virus common name (may wrap across lines) plus a hazard group `2`, `3`, `3*`, or `4`.  
- Repeated page chrome: `Biological agent`, `Human pathogen`, `hazard group`, `Taxonomy / notes`. Ignore.

Family and genus are **sticky**. They apply to following agent rows until replaced.

### 2.1 Hard stop

The virus tables **end on printed page 42**. Printed page 43 is not a catalogue page.

Do **not** extract the next page when it carries both:

- `Health and Safety Executive`  
- `Annex 1: Biological agents which may be used at less than the minimum containment conditions`

Example (`Hantaviridae`):

```text
Family Hantaviridae
Genus Orthohantavirus
Andes virus | 3 | In the Orthohantavirus andesense species
Bayou virus | 3 | In the Orthohantavirus bayoui species
```

becomes:

```text
Hantaviridae, Orthohantavirus, Andes virus, 3,
Hantaviridae, Orthohantavirus, Bayou virus, 3,
```

Taxonomy/notes text is **not** a virus name. Notes such as `Tick borne encephalitis virus (TBEV) – Far Eastern Subtype` stay attached to the current agent (Absettarov virus). They must not be concatenated onto the next agent (Alkhumra haemorrhagic fever virus).

## 3. Field rules

- Collapse internal newlines and squeeze whitespace in virus names.  
- Keep punctuation and diacritics (`Caño Delgadito virus`).  
- Hazard group: copy the cell (`3`, `3*`, `2`, `4`). The asterisk is a containment footnote in the source list, **not** Schedule 5.  
- Schedule 5: if `§` appears in any cell of the agent row, write `§`; otherwise blank. This 2026 PDF often omits the mark; the column still exists so older marked lists and fixtures can round-trip.  
- Do not invent Schedule 5 membership from SAPO notes or from `*`.

## 4. Object model (SOLID)

| Type | Responsibility |
| --- | --- |
| `PrintedPageWindow` | Inclusive bounds 27–42 |
| `PageHaltPolicy` / `AnnexTitleHaltPolicy` | Halt on the Annex 1 title page |
| `VirusSectionPageSelector` | INCLUDE vs HALT for one printed page |
| `TableExtractor` (Protocol) | Read PDF pages in that window into `TableRow` values |
| `PdfPlumberTableExtractor` | pdfplumber adapter (the only PDF library type) |
| `RowClassifier` | Label a row: ignore, start, family, genus, agent |
| `ApprovedVirusListParser` | Carry Family/Genus; emit `VirusRecord` |
| `CatalogueSourcePath` | Default parse document `docs/misc208.pdf` |
| `CatalogueOutputPath` | Default artefact `output/viruses.csv` |
| `LongFormatCsvWriter` | Write the five-column CSV |
| `ParseApprovedVirusList` | Orchestrate extractor → parser → sink |

`VirusRecord` is a frozen dataclass (Family, Genus, Virus, hazard group, schedule 5). Constructor injection only; tests supply a fake extractor.

## 5. Workflow

1. Open the PDF.  
2. Extract tables from **printed page 27 until printed page 42** (inclusive).  
3. Do **not** extend to the next page when it has the header `Health and Safety Executive` and `Annex 1: Biological agents which may be used at less than the minimum containment conditions`.  
4. Ignore rows until column 1 is `Viruses`.  
5. Classify each following row. Page 42 is the last source page; Annex 1 is never in the row stream.  
6. Write CSV to the standard output directory.

CLI (thin; no business rules). Defaults:

```text
docs/misc208.pdf      source PDF
output/viruses.csv     generated CSV
```

Directory **`docs/`** holds parse documents. Directory **`output/`** holds generated CSV (`viruses.csv`).

```bash
python -m virus_redteaming parse-viruses
python -m virus_redteaming parse-viruses --pdf docs/misc208.pdf --out output/viruses.csv
```

`--pdf` and `--out` are optional. When omitted, the CLI reads `docs/misc208.pdf` and writes `output/viruses.csv`.

## 6. Spot checks (acceptance)

Parsers must produce records that include the following tuples `(Family, Genus, Virus, HG, schedule 5)`.

### 6.1 Hantaviridae / Orthohantavirus

| Family | Genus | Virus | HG | schedule 5 |
| --- | --- | --- | --- | --- |
| Hantaviridae | Orthohantavirus | Andes virus | 3 | (blank) |
| Hantaviridae | Orthohantavirus | Bayou virus | 3 | (blank) |
| Hantaviridae | Orthohantavirus | Black Creek Canal virus | 3 | (blank) |
| Hantaviridae | Orthohantavirus | Caño Delgadito virus | 3 | (blank) |
| Hantaviridae | Orthohantavirus | Choclo virus | 3 | (blank) |

### 6.2 Flaviviridae / Orthoflavivirus

| Family | Genus | Virus | HG | schedule 5 |
| --- | --- | --- | --- | --- |
| Flaviviridae | Orthoflavivirus | Absettarov virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Alkhumra haemorrhagic fever virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Central European tick-borne encephalitis virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Dengue virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Far Eastern tick-borne encephalitis virus (formerly Russian spring–summer encephalitis virus) | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Hanzalova virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Hypr virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Israel turkey meningitis meningoencephalomyelitis virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Japanese encephalitis virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Kumlinge virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Kyasanur Forest disease virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Louping ill virus | 3* | (blank) |
| Flaviviridae | Orthoflavivirus | Murray Valley encephalitis virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Negishi virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Omsk haemorrhagic fever virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Powassan virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Rocio virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Sal Vieja virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | San Perlita virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Siberian tick-borne encephalitis virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Spondweni virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | St Louis encephalitis virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Usutu virus | 2 | (blank) |
| Flaviviridae | Orthoflavivirus | Wesselsbron virus | 3* | (blank) |
| Flaviviridae | Orthoflavivirus | West Nile fever virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Yellow fever virus | 3 | (blank) |
| Flaviviridae | Orthoflavivirus | Zika virus | 2 | (blank) |
| Flaviviridae | Orthoflavivirus | Other tick-borne encephalitis viruses known to be pathogenic in humans | 3 | (blank) |

Rejected extraction (do not emit as one Virus cell):

```text
Tick borne encephalitis virus (TBEV) – Far Eastern Subtype Alkhumra haemorrhagic fever virus
```

That string is Absettarov’s notes glued to the next agent.

## 7. Tests

- Unit: fake `TableExtractor`; Hantaviridae and Flaviviridae fixtures; exact field spot checks above.  
- Unit: page chrome ignored; sticky family/genus; `*` stays on HG; `§` maps to schedule 5 when present.  
- Unit: `PrintedPageWindow` includes 27 and 42, excludes 26 and 43; Annex 1 title halts; HSE header alone does not.  
- Integration: real `misc208.pdf` when present; no extracted row from printed page 43; no `Annex 1:` in the row stream; Hantaviridae five-row order; Alkhumra is its own virus.

## 8. Risks

- pdfplumber can merge `Family` + `Genus` into one cell — the classifier must split both.  
- Wrapped names must not become two agents.  
- Reading past page 42 would ingest Annex 1 and a second `Viruses` heading. The page selector is the primary stop; it must not be “page 27 to end of file”.
