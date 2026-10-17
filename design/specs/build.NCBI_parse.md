# build.NCBI_parse.md

**Status:** proposed  
**Companion spec:** [spec.NCBI_parse.md](spec.NCBI_parse.md)  
**Target:** `output/accession_criteria.csv`, `output/NCBI_representative_seq.csv`, and an `Accession` column on `output/genes.csv`  
**Scope:** clinical genes and genomes are not pathogen work (ADR 0004). This step does not call NCBI.

## Execution rule

Reading or editing this file does **not** create Python.

A request to **run this build** (this document named, or “run `build.NCBI_parse.md`”) **does** create the modules and the Pytest files in §2 and §4, then runs the unit tests in §4. It does not call NCBI.

Do not put this workflow in `catalogue/`. Do not import pdfplumber or Biopython. Do not hard-code a query phrase. The query text is read from `output/accessions.csv`.

## 0. Locked rules

| Rule | Value |
| --- | --- |
| Groups | Rows in `output/accessions.csv` that share one `Virus` cell. At most 5, ranks 1 through 5 |
| Bracket tags | Delete each complete `[...]`, including both brackets. Words outside the brackets stay, including `virus` |
| Words | Alphanumeric tokens split on `[^A-Za-z0-9]+`, lowercased, first-seen order, duplicates dropped |
| Header compare | Case-insensitive whole alphanumeric word |
| In order | Screened words appear in the header in that order. Other header words may sit between them. Highest priority |
| Adjacent | Those words sit next to each other in that order. Next priority, and only as a tie-break among in-order matches |
| Word count | Used when no file is in order. A count of 0 is not a candidate |
| Gene length | Residue count after the header line, whitespace removed. The `>` line is not counted |
| Upper cutoff | Longer than 40,000 bp is excluded. 40,000 bp is allowed |
| Tie | Lower `Rank` in `output/accessions.csv` |
| Query match | `Virus` equals `Query` after spaces at the two ends are removed. Case and spaces between words stay as written |
| `genes.csv` write | Temporary file in `output/`, flush, close, then one atomic replace. Do not write `genes.csv` in place |
| Commas | In `output/accession_criteria.csv`, `\` is written `\\` and `,` is written `\,` |
| Skipped matches | `human` does not match `Homo`. `Human insulin` does not match `human insulin` |

This step reads local files only. It does not call `Bio.Entrez`.

## 1. SOLID map

| Principle | How |
| --- | --- |
| S | Tag removal, word split, FASTA read, match, selection, comma escape, and each writer are separate types |
| O | A new match rule implements `HeaderMatch` without editing the writers |
| L | Unit-test fakes honour `FastaMeasure` and `CriteriaSink` |
| I | Selection does not write files. The `genes.csv` writer does not score headers |
| D | `RepresentativeParse` depends on Protocols. It does not open Entrez |

Package: `src/virus_redteaming/clinical_fasta/`. Add the types below. Do not add this work to `BiopythonEntrezClient`, `AccessionSearch`, or `ClinicalFastaDownload`.

Entrypoint: `python -m virus_redteaming.clinical_fasta parse`. No email. No `--min-length`. The 40,000 bp ceiling lives in this parse step.

## 2. Pseudocode per module

### 2.1 `clinical_fasta/screened_words.py`

```
ScreenedWords.MAX_BP is not here.
ScreenedWords.from_query(text) → tuple[str, ...]
    delete every complete [...] tag, brackets included
    split the remainder on [^A-Za-z0-9]+
    lowercase, drop empty, drop duplicates, keep first-seen order
    do not drop the word virus
    human[organism] mitochondrion genome → (human, mitochondrion, genome)
    virus[organism] → (virus,)
    [organism] → ()
```

### 2.2 `clinical_fasta/fasta_measure.py`

```
FastaMeasure.read(path) → measured record or missing
    path is output/clinical_genes/{accession}.fasta
    file absent → missing
    header ← first line, leading > removed
    gene length ← character count after that line, whitespace removed
    header words ← alphanumeric tokens of the header, lowercased
```

One header line is expected. The length does not include that line.

### 2.3 `clinical_fasta/header_match.py`

```
HeaderMatch
    in_order(header words, screened words) → bool
        walk the header once
        each next screened word may have other header words before it
    adjacent(header words, screened words) → bool
        some header slice equals the screened words with nothing between them
    matched_words(header words, screened words) → tuple[str, ...]
        screened words that occur in the header, in screened order
```

`human` compared with `homo` is false.

### 2.4 `clinical_fasta/representative_selection.py`

```
UPPER_BP = 40000
RepresentativeSelection.choose(scored rows) → one accession or none
    a row with a failure is not a candidate
    failure, first reason that applies:
        no screened words
        missing fasta
        longer than 40000 bp
        no word match
    candidates:
        1. if any candidate is in order, drop the rest
        2. among those, if any is adjacent, drop the rest
        3. else keep the highest word-match count above 0
        4. keep the largest gene length at or below UPPER_BP
        5. keep the lower rank
    Representative is 1 on that row and 0 on every other row in the group
    a row that was eligible and not chosen has an empty Failure
```

### 2.5 `clinical_fasta/comma_escape.py`

```
CommaEscape.encode(text) → str
    replace \ with \\
    replace , with \,
```

Apply this to every text field of `output/accession_criteria.csv` before write. `Representative` stays the last column.

### 2.6 `clinical_fasta/criteria_sink.py`

```
AtomicCriteriaSink(destination).write(rows) → Path
    destination is output/accession_criteria.csv
    one row per accession, accessions.csv order
    header Query,Rank,Accession,ScreenedWords,InOrderMatch,AdjacentMatch,WordMatchCount,MatchedWords,GeneLength,WithinUpperCutoff,Header,Failure,Representative
    GeneLength empty when the FASTA is missing
    WithinUpperCutoff is 1 only when GeneLength is present and GeneLength <= 40000
    temp file in output/, flush, close, os.replace
    on failure before replace: delete the temp file and leave the previous destination in place
```

### 2.7 `clinical_fasta/representative_sink.py`

```
AtomicRepresentativeSink(destination).write(chosen) → Path
    destination is output/NCBI_representative_seq.csv
    one row per group that has a chosen sequence
    a group with no chosen sequence is absent
    header Query,Accession,GeneLength,Sequence,Representative
    Sequence is the residue text, whitespace removed, no header
    Representative is 1 on every row
    same atomic replace as §2.6
```

### 2.8 `clinical_fasta/genes_align.py`

```
AtomicGenesAligner(destination).write(original rows, chosen by query) → Path
    destination is output/genes.csv
    for each data row, query ← Virus with spaces removed at the two ends
    if a chosen criteria row has that same trimmed Query, set Accession
    two rows with the same Virus text receive the same accession
    no chosen row → Accession empty
    if Accession is absent, append it as the last column
    if Accession is present, fill that column and do not add another
    other columns and row order stay as read
    write the complete table to a uniquely named temp file in output/
    flush, close, os.replace onto output/genes.csv
    do not open genes.csv for in-place writing
    on failure: delete the temp file and leave the previous genes.csv unchanged
```

### 2.9 `clinical_fasta/parse_workflow.py`

```
RepresentativeParse(accessions, fasta directory, screened words, measure, match, selection, criteria sink, representative sink, genes aligner)
    run() → tuple[criteria path, representative path, genes path]
        read output/accessions.csv in order
        group by Virus cell
        for each group:
            words ← ScreenedWords.from_query(Virus cell)
            score each accession with FastaMeasure and HeaderMatch
            RepresentativeSelection.choose
        write the three outputs in this order:
            accession_criteria.csv
            NCBI_representative_seq.csv
            genes.csv
    this type does not open a socket
```

### 2.10 `clinical_fasta/__main__.py`

Add a `parse` subcommand. It takes no filename and no `--min-length`.

```
python -m virus_redteaming.clinical_fasta parse
    read output/accessions.csv, output/clinical_genes/, and output/genes.csv
    print the three output paths, one per line
    exit 0 when the three files are replaced
    a package write error → stderr, exit 1
```

`search` and `download` stay as they are.

## 3. Call order

```
output/accessions.csv
  → group by Virus cell
  → ScreenedWords.from_query
  → for each accession:
        FastaMeasure.read(output/clinical_genes/{accession}.fasta)
        HeaderMatch
        first failure, or empty Failure
  → RepresentativeSelection.choose
  → AtomicCriteriaSink → output/accession_criteria.csv
  → AtomicRepresentativeSink → output/NCBI_representative_seq.csv
  → AtomicGenesAligner → output/genes.csv
```

## 4. Tests

Unit tests live in `tests/unit/clinical_fasta/`. They use local fixtures and do not call NCBI.

| Test | Asserts |
| --- | --- |
| `test_screened_words_delete_complete_bracket_tags` | `human[organism] mitochondrion genome` yields `human`, `mitochondrion`, `genome`. Both brackets are gone. |
| `test_screened_words_keep_virus_outside_brackets` | `virus[organism]` yields `virus`. |
| `test_screened_words_empty_when_only_a_tag_remains` | `[organism]` yields no words. |
| `test_header_match_counts_whole_words` | `mitochondrion` and `genome` match the worked header. `human` does not match `Homo`. |
| `test_in_order_allows_words_between` | `mitochondrion` then `genome` matches when other header words sit between them. The reverse order does not. |
| `test_adjacent_requires_words_next_to_each_other` | Adjacent is true only when the screened words form one contiguous slice. |
| `test_selection_prefers_in_order_then_adjacent_then_length` | An in-order file beats a higher word count. An adjacent in-order file beats a gapped in-order file. Otherwise the longest file at or below 40,000 bp wins. Equal length keeps the lower rank. |
| `test_selection_rejects_length_above_40000` | 40,000 bp can win. 40,001 bp has `Failure` `longer than 40000 bp`. |
| `test_missing_fasta_is_a_criteria_failure` | A missing file writes a criteria row with `Failure` `missing fasta`, empty `GeneLength`, empty `Header`, and `Representative` 0. |
| `test_no_screened_words_fails_every_row` | `Failure` is `no screened words` and `Representative` is 0. |
| `test_no_word_match_is_reported` | A present FASTA whose header matches nothing has `Failure` `no word match`. |
| `test_criteria_escapes_commas_and_keeps_representative_last` | A comma in the header is written `\,`. `Representative` is the last column. |
| `test_representative_file_contains_only_chosen_sequences` | One row per chosen group. `Representative` is 1. A group with no winner is absent. |
| `test_genes_csv_adds_accession_once` | A file without `Accession` gains that column at the end. A second parse does not add another `Accession` column. |
| `test_genes_csv_repeats_one_accession_for_duplicate_virus_text` | Two rows with the same `Virus` text receive the same accession. |
| `test_genes_csv_match_trims_ends_only` | Spaces at the ends match. `Human insulin` does not match `human insulin`. |
| `test_genes_csv_replace_is_atomic` | A failure before replace deletes the temp file and leaves the previous `genes.csv` unchanged. |

```bash
python3 -m pytest tests/unit/clinical_fasta -q
```

## 5. Packaging

No new dependency. This step does not import Biopython.
