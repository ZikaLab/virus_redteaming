# build.NCBI_parse.md

**Status:** proposed  
**Companion spec:** [spec.NCBI_parse.md](spec.NCBI_parse.md)  
**Target:** `output/accession_criteria.csv`, `output/NCBI_representative_seq.csv`, and an `Accession` column on `output/genes.csv`  
**Scope:** clinical genes and genomes are not pathogen work (ADR 0004). This step does not call NCBI.

## Execution rule

Reading or editing this file does **not** create Python.

A request to **run this build** (this document named, or “run `build.NCBI_parse.md`”) **does** create the modules and the Pytest files in §2, §4, and [TESTING](#testing), then runs the commands in TESTING. It does not call NCBI.

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
| Match continuation | Only after the word-count tie. Lowest sum of words that extend each matched word before a clause boundary |
| Gene length | Residue count after the header line, whitespace removed. The `>` line is not counted |
| Upper cutoff | Longer than 40,000 bp is excluded. 40,000 bp is allowed |
| Tie | Lower `Rank` in `output/accessions.csv` |
| Query match | `Virus` equals `Query` after spaces at the two ends are removed. Case and spaces between words stay as written |
| `genes.csv` write | Temporary file in `output/`, flush, close, then one atomic replace. Do not write `genes.csv` in place |
| Commas | `accession_criteria.csv` only: `csv.writer` and `csv.reader` with `QUOTE_NONE`, `escapechar="\\"`, and `doublequote=False`. That pair escapes and unescapes once. There is no second encode or decode. `genes.csv` and `NCBI_representative_seq.csv` use ordinary CSV quotes |
| Skipped matches | `human` does not match `Homo`. `Human insulin` does not match `human insulin` |

This step reads local files only. It does not call `Bio.Entrez`.

## 1. SOLID map

| Principle | How |
| --- | --- |
| S | Tag removal, word split, FASTA read, match, selection, criteria read, and each writer are separate types |
| O | A new match rule implements `HeaderMatch` without editing the writers |
| L | Unit-test fakes honour `AccessionGroupSource`, `FastaMeasure`, `CriteriaSink`, `CriteriaRepresentativeSource`, and `GenesAligner` |
| I | Selection does not write files. `AtomicGenesAligner` does not open the criteria file or score headers |
| D | `RepresentativeParse` calls the injected Protocols. It does not construct `AccessionHitCsvSource` or `CriteriaCsvRepresentativeSource` itself, and it does not open Entrez |

Package: `src/virus_redteaming/clinical_fasta/`. Add the types below. Do not add this work to `BiopythonEntrezClient`, `AccessionSearch`, or `ClinicalFastaDownload`.

Entrypoint: `python -m virus_redteaming.clinical_fasta parse`. No email. No `--min-length`. The 40,000 bp ceiling lives in this parse step.

## 2. Pseudocode per module

### 2.0a `clinical_fasta/models.py`

Add these frozen values. Leave the existing search and FASTA values in place.

```
CriteriaRow
    query, rank, accession
    screened words
    in-order flag, adjacent flag, word-match count, matched words
    gene length or empty, within-cutoff flag
    header or empty, failure or empty, representative flag
    sequence text or empty

MeasuredFasta
    header, header words, gene length, sequence

ChosenAccession
    query, accession
```

`query` on `CriteriaRow` and `ChosenAccession` is the original text. The criteria CSV writer escapes it on the way out, and the criteria CSV reader restores it on the way in. `AccessionHit` already holds `virus`, `rank`, and `accession`; the group reader returns that type.

### 2.0b `clinical_fasta/protocols.py`

```
AccessionGroupSource.read() → tuple[AccessionHit, ...] in file order
FastaMeasure.read(path) → MeasuredFasta or missing
CriteriaSink.write(rows) → Path
RepresentativeSink.write(chosen) → Path
CriteriaRepresentativeSource.read() → tuple[ChosenAccession, ...]
    the concrete class is CriteriaCsvRepresentativeSource, not this Protocol name
GenesAligner.write(chosen) → Path
```

### 2.0c `clinical_fasta/paths.py`

```
CRITERIA_FILENAME = accession_criteria.csv
REPRESENTATIVE_FILENAME = NCBI_representative_seq.csv
```

`genes.csv`, `accessions.csv`, and `clinical_genes/` stay the names already in this module.

### 2.0d `clinical_fasta/errors.py`

Reuse `NcbiInputError` for a missing or unreadable table, a missing `Virus`, `Rank`, or `Accession` column, a rank that is not an integer, a FASTA file that is present but has no header line, and two chosen rows whose trimmed queries are equal but whose accessions differ. Reuse `FastaWriteError` when an atomic replace fails. Do not add a new exception for a row listed in `Failure`; that row is data, not a raised error.

### 2.0e `clinical_fasta/accession_source.py`

Add `AccessionHitCsvSource` beside the existing `AccessionCsvSource`. Do not change `AccessionCsvSource`; download still uses it for distinct accession strings.

```
AccessionHitCsvSource(path).read() → tuple[AccessionHit, ...]
    path is output/accessions.csv
    require the Virus, Rank, and Accession headers, else NcbiInputError
    missing file or no data rows → NcbiInputError
    Virus and Accession cells must be non-blank, else NcbiInputError
    Accession must match ^[A-Z]{1,6}_?[0-9]+(\.[0-9]+)?$, else NcbiInputError
    Rank must be an integer from 1 through 5, else NcbiInputError
    return every data row in file order
    a repeated Virus cell stays repeated
    do not drop or reorder rows
    after the rows are grouped, a group with more than 5 rows, or a repeated rank, → NcbiInputError
```

### 2.1 `clinical_fasta/screened_words.py`

```
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
FastaMeasure.read(path) → MeasuredFasta or missing
    path is output/clinical_genes/{accession}.fasta
    file absent → missing
    file present but empty, or first line does not start with > → NcbiInputError
    a second line that starts with > → NcbiInputError
    header ← first line, leading > removed
    sequence ← every character after that line, whitespace removed
    gene length ← length of sequence
    header words ← alphanumeric tokens of the header, lowercased
```

The length does not include the header line. `sequence` is what `NCBI_representative_seq.csv` stores.

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
    continuation_penalty(original header, matched words) → int
        for each matched word, count alphanumeric words after each whole-word hit
        stop at the end or at , ; : ( ) [ ] /
        repeated hits of one word keep the lowest count
        return the sum, or 0 when no word matched
```

`human` compared with `homo` is false.

### 2.4 `clinical_fasta/representative_selection.py`

```
UPPER_BP = 40000
RepresentativeSelection.choose(scored rows) → one accession or none
    a row with a failure is not a candidate
    fill GeneLength, Header, the match flags, and MatchContinuationPenalty whenever the FASTA is present
    match flags are 0 when there are no screened words
    MatchContinuationPenalty is empty when the FASTA is missing, and 0 when no screened word matched
    failure, first reason that applies, after that measurement:
        no screened words
        missing fasta
        longer than 40000 bp
        no word match
    missing fasta leaves GeneLength and Header empty and WithinUpperCutoff 0
    longer than 40000 bp still keeps the measured header and match flags
    candidates:
        if any candidate is in order:
            keep only those
            if any of those is adjacent, keep only the adjacent ones
        else:
            keep only the highest word-match count above 0
            then keep the lowest MatchContinuationPenalty
        then keep the largest gene length at or below UPPER_BP
        then keep the lower rank
    Representative is 1 on that row and 0 on every other row in the group
    a row that was eligible and not chosen has an empty Failure
```

### 2.5 Criteria CSV escape

Do not add `comma_escape.py`. Do not call a separate encode or decode function.

`csv.writer` and `csv.reader` for `accession_criteria.csv` use `quoting=QUOTE_NONE`, `escapechar="\\"`, and `doublequote=False`. The writer turns `\` into `\\` and `,` into `\,` once. The matching reader turns those sequences back once while it splits the row. A field read from that file is the original text.

`genes.csv` and `NCBI_representative_seq.csv` stay ordinary CSV: a field that contains a comma is wrapped in quotes, and a quote inside a field is doubled.

### 2.6 `clinical_fasta/criteria_sink.py`

```
AtomicCriteriaSink(destination).write(rows) → Path
    destination is output/accession_criteria.csv
    one row per accession, accessions.csv order
    header Query,Rank,Accession,ScreenedWords,InOrderMatch,AdjacentMatch,WordMatchCount,MatchedWords,MatchContinuationPenalty,GeneLength,WithinUpperCutoff,Header,Failure,Representative
    pass the original field text to csv.writer
    writer settings: quoting QUOTE_NONE, escapechar "\\", doublequote false
    do not escape the text before handing it to the writer
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

### 2.8 `clinical_fasta/criteria_representatives.py`

The Protocol name stays `CriteriaRepresentativeSource`. The class in this file is `CriteriaCsvRepresentativeSource`.

```
CriteriaCsvRepresentativeSource(path).read() → tuple[ChosenAccession, ...]
    path is the criteria file just written
    csv.reader settings: quoting QUOTE_NONE, escapechar "\\", doublequote false
    the field text is the original text; do not decode it again
    missing file, empty file, or a missing Query, Accession, or Representative header → NcbiInputError
    Representative must be 0 or 1, else NcbiInputError
    keep rows whose Representative is 1
    a chosen row with a blank query or accession → NcbiInputError
    query on ChosenAccession has spaces removed at the two ends
    two chosen rows with the same trimmed query and the same accession collapse to one
    two chosen rows with the same trimmed query and different accessions → NcbiInputError
```

### 2.8a `clinical_fasta/genes_align.py`

```
AtomicGenesAligner(destination).write(chosen) → Path
    destination is output/genes.csv
    chosen is tuple[ChosenAccession, ...]
    read genes.csv itself; do not open the criteria file
    for each data row, query ← Virus with spaces removed at the two ends
    if a ChosenAccession has that query, set Accession
    two genes.csv rows with the same Virus text receive the same accession
    no chosen row for that query → Accession empty
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
RepresentativeParse(group source, fasta directory, screened words, measure, match, selection, criteria sink, representative sink, representative source, genes aligner)
    run() → tuple[criteria path, representative path, genes path]
        hits ← group source.read(), in file order
        one group per exact Virus cell, including rows that are not next to each other
        criteria rows stay in accessions.csv order
        representative rows follow the first time each Virus cell appears
        for each group:
            words ← ScreenedWords.from_query(hit.virus)
            score each accession with FastaMeasure and HeaderMatch
            RepresentativeSelection.choose
        criteria path ← criteria sink
        representative path ← representative sink
        chosen ← representative source.read()
        genes path ← genes aligner.write(chosen)
    the workflow wires representative source to the criteria path just returned
    a later write failure leaves the earlier replaced files in place
    parse can be run again
    this type does not open a socket
```

### 2.10 `clinical_fasta/__main__.py`

Add a `parse` subcommand. It takes no filename and no `--min-length`.

```
python -m virus_redteaming.clinical_fasta parse
    branch on the command before reading --min-length
    parse does not use that flag
    read output/accessions.csv, output/clinical_genes/, and output/genes.csv
    print the three output paths, one per line
    exit 0 when the three files are replaced
    missing table, missing Virus column, a blank or malformed accession,
    a bad rank, or a present FASTA that is empty, has no > line, or has a second header
        → NcbiInputError on stderr, exit 1
    a package write error → stderr, exit 1
```

`search` and `download` stay as they are. Their `--min-length` handling is unchanged.

## 3. Call order

```
output/accessions.csv
  → keep file order
  → one group per exact Virus cell, even when its rows are not contiguous
  → ScreenedWords.from_query
  → for each accession:
        FastaMeasure.read(output/clinical_genes/{accession}.fasta)
        HeaderMatch
        first failure, or empty Failure
  → RepresentativeSelection.choose
  → AtomicCriteriaSink → output/accession_criteria.csv
  → AtomicRepresentativeSink → output/NCBI_representative_seq.csv
  → representative source.read() uses csv.reader with the same QUOTE_NONE and \ escape
  → AtomicGenesAligner.write(chosen) replaces output/genes.csv
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
| `test_criteria_escapes_commas_and_keeps_representative_last` | `csv.writer` writes a comma as `\,` with no surrounding quotes. `Representative` is the last column. The matching `csv.reader` returns the original comma. |
| `test_accession_hit_source_keeps_rank_and_repeats` | `AccessionHitCsvSource` returns every row as `AccessionHit`, in order, including a repeated `Virus` cell. A missing column or a non-integer rank raises `NcbiInputError`. |
| `test_criteria_reader_uses_the_escape_once` | `csv.writer` emits `a\,b` for the text `a,b`. `csv.reader` with the same settings returns `a,b`. No encode or decode function runs before or after that pair. |
| `test_two_winners_for_one_query_are_rejected` | Two `Representative` 1 rows with the same trimmed query and different accessions raise `NcbiInputError`. |
| `test_genes_csv_matches_a_query_with_a_comma` | A query that contains a comma is written by `csv.writer` as `\,`. `csv.reader` restores the comma, and that value matches the original `genes.csv` cell. |
| `test_overlong_fasta_keeps_match_fields` | A sequence longer than 40,000 bp keeps its header and match flags, with `Failure` `longer than 40000 bp`. |
| `test_no_screened_words_still_measures_a_present_fasta` | `Failure` is `no screened words`. Gene length and header are filled when the file exists. |
| `test_parse_groups_a_repeated_virus_cell` | The same `Virus` cell in non-adjacent rows is one group. Criteria rows stay in file order. |
| `test_parse_command_does_not_require_min_length` | `parse` runs without `--min-length` and does not call NCBI. |
| `test_parse_rejects_a_missing_table` | A missing accession table or a missing `Virus` column raises `NcbiInputError`. |
| `test_accession_hit_source_rejects_bad_ranks_and_ids` | A rank outside 1 through 5, a repeated rank, more than 5 rows in one group, a blank cell, or a malformed accession raises `NcbiInputError`. |
| `test_fasta_measure_rejects_a_bad_file` | An empty file, a file that does not start with `>`, or a second header line raises `NcbiInputError`. |
| `test_criteria_reader_rejects_a_bad_table` | A missing criteria header, a `Representative` value other than 0 or 1, or a chosen row with a blank query or accession raises `NcbiInputError`. |
| `test_representative_and_genes_use_ordinary_csv_quotes` | A comma in those files is wrapped in quotes. It is not written as `\,`. |
| `test_criteria_and_representative_sinks_replace_atomically` | A failure before replace deletes the temp file and leaves the previous destination unchanged. |
| `test_representative_file_contains_only_chosen_sequences` | One row per chosen group. `Representative` is 1. A group with no winner is absent. |
| `test_genes_csv_adds_accession_once` | A file without `Accession` gains that column at the end. A second parse does not add another `Accession` column. |
| `test_genes_csv_repeats_one_accession_for_duplicate_virus_text` | Two rows with the same `Virus` text receive the same accession. |
| `test_genes_csv_match_trims_ends_only` | Spaces at the ends match. `Human insulin` does not match `human insulin`. |
| `test_genes_csv_replace_is_atomic` | A failure before replace deletes the temp file and leaves the previous `genes.csv` unchanged. |

```bash
python3 -m pytest tests/unit/clinical_fasta/test_parse.py tests/integration/test_clinical_fasta_parse.py -q
```

## 5. Packaging

No new dependency. This step does not import Biopython.

## TESTING

This section is the pass/fail contract. A parse change is complete only when every named test exists and passes. §4 lists the first unit tests. The criteria below are what those tests, and the tests added here, must prove.

The tests use local fixtures. They do not call NCBI, do not import Biopython, and do not read the repository `output/` directory. A temporary directory stands in for `output/`.

Unit tests exercise one rule, or the workflow through Protocol fakes. Integration tests run `parse` through `main` with the real readers and writers wired together.

### Unit

File: `tests/unit/clinical_fasta/test_parse.py`

| Test | Given | Then |
| --- | --- | --- |
| `test_screened_words_delete_complete_bracket_tags` | `human[organism] mitochondrion genome` | The words are `human`, `mitochondrion`, `genome`. Neither bracket remains. |
| `test_screened_words_keep_virus_outside_brackets` | `virus[organism]` | The only word is `virus`. |
| `test_screened_words_empty_when_only_a_tag_remains` | `[organism]` | There are no words. |
| `test_screened_words_delete_every_complete_tag` | `human[organism] mitochondrion[title] genome[SLEN]` | The words are `human`, `mitochondrion`, `genome`. `[title]` and `[SLEN]` are gone. |
| `test_screened_words_keep_first_seen_order` | `Insulin insulin gene gene` | The words are `insulin`, then `gene`. Case is folded. The repeat is dropped. |
| `test_header_match_counts_whole_words` | Header words `homo`, `sapiens`, `mitochondrion`, `complete`, `genome` | `mitochondrion` and `genome` match. `human` does not match `homo`. |
| `test_header_match_is_case_insensitive` | Query `insulin` and a FASTA header `Insulin` | The header word matches. `InOrderMatch` is 1 and the row is chosen. |
| `test_continuation_penalty_measures_each_worked_header` | The five header fragments in `bug.NCBI_parse.md` | Their penalties are 0, 1, 4, 1, and 2. |
| `test_continuation_penalty_stops_at_each_boundary` | A matched word followed by one word and then each boundary character | Each of `,`, `;`, `:`, `(`, `)`, `[`, `]`, and `/` stops the count. The end of the header also stops it. |
| `test_continuation_penalty_keeps_the_nearest_repeat` | The same word occurs twice | The penalty uses the occurrence with fewer following words. |
| `test_selection_uses_continuation_penalty_before_length` | Two fallback rows. One is longer and has a higher penalty | The lower penalty wins. |
| `test_parse_chooses_the_exact_insulin_label` | The five current insulin headers and short sequences. The IGF2 sequence is the longest eligible sequence | The representative accession is `NG_007114.1`. |
| `test_parse_keeps_the_longest_tied_mitochondrion_header` | The five current mitochondrion headers. The whole-genome-shotgun sequence is the longest | The representative accession is `OZ560341.1`. |
| `test_in_order_allows_words_between` | The same header words | `mitochondrion` then `genome` is in order. `genome` then `mitochondrion` is not. |
| `test_adjacent_requires_words_next_to_each_other` | `mitochondrion` and `genome` have `complete` between them | Adjacent is false. Adjacent is true when those two words are one contiguous slice. |
| `test_worked_header_matches_mitochondrion_and_genome` | Query `human[organism] mitochondrion genome` and header `OZ567094.1 Homo sapiens genome assembly, organelle: mitochondrion` | `ScreenedWords` is `human;mitochondrion;genome`. `MatchedWords` is `mitochondrion;genome`. `WordMatchCount` is 2. `InOrderMatch` and `AdjacentMatch` are 0. `human` is not a matched word. The header comma is written `\,` and read back as a comma. `Representative` is the last column. The representative sequence is the residues only. |
| `test_gene_length_ignores_the_header_and_whitespace` | A FASTA whose header is `insulin gene` and whose following text is `AC GT` | `GeneLength` is 4. The header stored does not include `>`. The representative sequence is `ACGT`. |
| `test_selection_prefers_in_order_then_adjacent_then_length` | Scored rows that differ by order, adjacency, length, and rank | An in-order row beats a higher word count. An adjacent in-order row beats a gapped in-order row. Otherwise the longest row at or below 40,000 bp wins. Equal length keeps the lower rank. |
| `test_in_order_beats_the_same_words_reversed` | FASTA text. Query `mitochondrion genome`. A longer header is `genome mitochondrion`. A shorter header is `mitochondrion complete genome` | The shorter in-order file wins. The reversed file has an empty `Failure` and `Representative` 0. |
| `test_adjacent_beats_a_longer_gapped_match` | FASTA text. Query `mitochondrion genome`. A longer header is `mitochondrion complete genome`. A shorter header is `mitochondrion genome` | The shorter adjacent file wins. |
| `test_equal_fasta_length_keeps_the_lower_rank` | Two FASTA files with the same header and the same length. Ranks 1 and 2 | Rank 1 wins. |
| `test_selection_rejects_length_above_40000` | One 40,000 bp FASTA and one 40,001 bp FASTA for the same query | 40,000 bp is `Representative` 1 and `WithinUpperCutoff` 1. 40,001 bp has `Failure` `longer than 40000 bp`, `Representative` 0, and `WithinUpperCutoff` 0. |
| `test_eligible_loser_keeps_an_empty_failure` | Two matching FASTA files under 40,000 bp | The shorter row has an empty `Failure` and `Representative` 0. The chosen row also has an empty `Failure`. |
| `test_missing_fasta_is_a_criteria_failure` | An accession with no FASTA file | The criteria row has `Failure` `missing fasta`, empty `GeneLength`, empty `Header`, and `Representative` 0. |
| `test_no_screened_words_fails_every_row` | Query `[organism]` and no FASTA file | `Failure` is `no screened words`, which comes before `missing fasta`. `Representative` is 0. The representative file has no data row. |
| `test_no_screened_words_still_measures_a_present_fasta` | Query `[organism]` and a present FASTA | `Failure` is `no screened words`. Gene length and header are filled. The three match flags are 0. |
| `test_no_word_match_is_reported` | A present FASTA whose header shares no screened word | `Failure` is `no word match`. |
| `test_overlong_fasta_keeps_match_fields` | A matching FASTA longer than 40,000 bp | Header and match flags stay filled. `Failure` is `longer than 40000 bp`. `WithinUpperCutoff` is 0. |
| `test_overlong_with_no_match_reports_length_first` | A FASTA longer than 40,000 bp whose header shares no screened word | `Failure` is `longer than 40000 bp`. It is not `no word match`. |
| `test_overlong_in_order_loses_to_a_shorter_partial_match` | Query `human insulin`. A 40,001 bp header is `human insulin`. A 10 bp header is `insulin` | The long file has `Failure` `longer than 40000 bp` and `InOrderMatch` 1. The short partial match is the representative. |
| `test_no_winner_leaves_the_genes_accession_blank` | A genes.csv row whose query has no representative | `Accession` is added and left empty. The other cells stay as read. |
| `test_criteria_escapes_commas_and_keeps_representative_last` | A query `a,b` and a header `x,y` | The file contains `\,` and no quotes around that comma. The reader returns the comma. `Representative` is the last column. |
| `test_criteria_reader_uses_the_escape_once` | The text `a,b` passed straight to `csv.writer` | The file contains `a\,b`, not a second layer of backslashes. The matching reader returns `a,b`. |
| `test_backslash_is_escaped_once` | The text `a\b` passed straight to `csv.writer` | The file contains `a\\b`. The matching reader returns `a\b`. |
| `test_same_accession_winners_collapse_to_one` | Two `Representative` 1 rows, same trimmed query, same accession | The reader returns one `ChosenAccession`. End spaces on the query are removed. |
| `test_two_winners_for_one_query_are_rejected` | Two `Representative` 1 rows, same trimmed query, different accessions | `NcbiInputError`. |
| `test_criteria_reader_rejects_a_bad_table` | A missing file, a missing required header, a `Representative` other than 0 or 1, or a chosen row with a blank query or accession | `NcbiInputError`. |
| `test_accession_hit_source_keeps_rank_and_repeats` | Rows whose `Virus` cell repeats, with a different rank | Every row comes back as `AccessionHit`, in file order. A missing column or a non-integer rank raises `NcbiInputError`. |
| `test_accession_hit_source_rejects_bad_ranks_and_ids` | A rank outside 1 through 5, a repeated rank, more than 5 rows in one group, a blank cell, or a malformed accession | `NcbiInputError`. |
| `test_fasta_measure_rejects_a_bad_file` | An empty file, a file that does not start with `>`, or a second header line | `NcbiInputError`. An absent path is missing, not an error. |
| `test_bad_fasta_is_an_input_error` | A present empty FASTA during parse | `NcbiInputError`. No criteria file is written. |
| `test_parse_groups_a_repeated_virus_cell` | The same `Virus` cell on non-adjacent rows | One group. Criteria rows stay in file order. One representative for that group. Representative-file order follows the first time each `Virus` cell appears. |
| `test_parse_scores_through_injected_fakes` | Fakes for the group source, FASTA measure, both sinks, the criteria opener, and the genes aligner | The workflow calls those fakes. It does not construct the CSV classes. The genes aligner receives the tuple returned by the opener, including a sentinel accession that selection did not choose. |
| `test_representative_file_contains_only_chosen_sequences` | One group with a winner and one group with no word match | The representative file has one data row. `Representative` is 1. The losing group is absent. |
| `test_representative_and_genes_use_ordinary_csv_quotes` | A comma in the query | Those two files wrap the field in quotes. They do not write `\,`. |
| `test_ordinary_csv_doubles_an_internal_quote` | A query `say "hi"` | `genes.csv` and the representative file contain `say ""hi""`. They do not write a backslash escape. |
| `test_genes_csv_matches_a_query_with_a_comma` | The same comma query in `genes.csv` and in the criteria file | The criteria reader restores the comma, and that value matches the `genes.csv` cell. |
| `test_genes_csv_adds_accession_once` | A genes file with no `Accession` column, parsed twice | The column is last. The second parse does not add another `Accession` column. |
| `test_genes_csv_repeats_one_accession_for_duplicate_virus_text` | Two genes.csv rows with the same `Virus` text | Both rows receive the same accession. |
| `test_genes_csv_match_trims_ends_only` | ` human insulin ` and `Human insulin` | The end spaces match. The different case does not. |
| `test_genes_csv_updates_an_accession_column_in_place` | Header `Family,Virus,Accession,Note` and a cell `STALE`. The first winner is the longer FASTA. That FASTA is then changed so it no longer matches | `Accession` stays between `Virus` and `Note`. There is still one `Accession` column. `STALE` is replaced by the first winner, then by the new winner. `Note` stays `keep`. |
| `test_criteria_and_representative_sinks_replace_atomically` | `os.replace` fails | The temp file is deleted. The previous destination is unchanged. |
| `test_genes_csv_replace_is_atomic` | `os.replace` fails while replacing `genes.csv` | The temp file is deleted. The previous `genes.csv` is unchanged. |
| `test_later_write_failure_keeps_the_earlier_files` | The criteria and representative files are replaced, then `os.replace` fails for `genes.csv` | The new criteria and representative files remain. The previous `genes.csv` remains. Its temp file is deleted. |
| `test_missing_genes_csv_leaves_the_earlier_tables` | Accessions and a FASTA exist. `genes.csv` does not | `NcbiInputError`. The criteria and representative files from this run remain. |
| `test_parse_command_does_not_require_min_length` | `main(["parse"])` with no `--min-length` | Exit 0. The three paths are printed. NCBI is not constructed. |
| `test_parse_rejects_a_missing_table` | No accession table, then a table with no `Virus` column | Exit 1. The error names the missing file or the missing header. |
| `test_parse_command_rejects_min_length` | `main(["parse", "--min-length", "10"])` | The process exits with status 2. Parse does not run. |

### Integration

File: `tests/integration/test_clinical_fasta_parse.py`

These tests call `main(["parse"])`. The object graph is the one `__main__` builds. The working directory is a temporary directory. NCBI construction is a failure.

`test_parse_command_writes_the_three_tables`

Given this `output/` tree:

- `genes.csv` header `Family,Genus,Virus,Human pathogen hazard group,Schedule 5`, with these data rows:
  - `alpha`, `beta`, `human[organism] mitochondrion genome`, `group`, `five`
  - empty, empty, ` human insulin `, empty, empty
  - empty, empty, `[organism]`, empty, empty
  - empty, empty, `Human insulin`, empty, empty
  - `alpha`, `beta`, `human[organism] mitochondrion genome`, `group`, `five`
- `accessions.csv` in this order:
  - `human[organism] mitochondrion genome`, rank 1, `NG_000001.1`, header `OZ567094.1 Homo sapiens genome assembly, organelle: mitochondrion`, sequence `ACGTACGT`
  - same query, rank 2, `NG_000002.1`, header `Homo sapiens mitochondrion`, sequence of 30 `A`
  - same query, rank 3, `NG_000003.1`, header `genome mitochondrion`, sequence of 12 `A`
  - same query, rank 4, `NG_000004.1`, no FASTA file
  - same query, rank 5, `NG_000005.1`, header `genome of the mitochondrion`, sequence of 40,001 `A`
  - `human insulin`, rank 1, `NG_000011.1`, header `human insulin`, sequence `AC`
  - `human insulin`, rank 2, `NG_000012.1`, header `human insulin`, sequence `ACGT`
  - `[organism]`, rank 1, `NG_000021.1`, header `kept header`, sequence `AAAA`

Then:

1. Exit 0. Stdout is the three output paths. NCBI is not constructed.
2. Criteria rows stay in accession-file order. There are 8 data rows. `Representative` is the last column.
3. `NG_000003.1` is the mitochondrion representative: word count 2, not in order, length 12. Rank 1 is an eligible loser with an empty `Failure`. Rank 2 has a word count of 1, an empty `Failure`, and `Representative` 0. Rank 4 is `missing fasta` with empty length and header. Rank 5 keeps its header and match flags, with `Failure` `longer than 40000 bp` and `WithinUpperCutoff` 0.
4. The rank 1 header comma is stored as `\,` in the criteria file and comes back as a comma. The criteria file does not wrap that comma in quotes.
5. `NG_000012.1` is the insulin representative. `NG_000011.1` has an empty `Failure` and `Representative` 0. Both insulin rows are in order and adjacent.
6. The `[organism]` row has `Failure` `no screened words`, gene length 4, header `kept header`, and match flags 0.
7. The representative file has two data rows, in first-seen query order: `NG_000003.1` then `NG_000012.1`. Each `Representative` is 1. Sequences are `AAAAAAAAAAAA` and `ACGT`, with no `>` and no whitespace. `[organism]` is absent.
8. `genes.csv` keeps its five original columns and appends `Accession` once, at the end. The two mitochondrion rows receive `NG_000003.1`. ` human insulin ` receives `NG_000012.1`. `[organism]` and `Human insulin` stay blank. `alpha` and `beta` stay on the mitochondrion rows.

`test_parse_command_second_run_keeps_one_accession_column`

Given the same tree, after `parse` has already added `Accession`, run `parse` again.

Then exit 0. The header contains `Accession` once, still last. The accession values from the first run are unchanged.

`test_parse_command_bad_fasta_leaves_genes_unchanged`

Given a genes.csv row `insulin` with note `keep-me`, one accession for that query, an empty FASTA file for that accession, and an existing criteria file whose text is `previous`.

Then exit 1. Stderr reports the bad header. `genes.csv` is still the original text. The criteria file is still `previous`. No temporary file remains.

### Commands

```bash
python3 -m pytest tests/unit/clinical_fasta/test_parse.py tests/integration/test_clinical_fasta_parse.py -q
```

The integration file has no `network` marker. It runs in the default suite. It does not require `NCBI_EMAIL` or `NCBI_LIVE_TEST`.
