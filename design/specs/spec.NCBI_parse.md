# spec.NCBI_parse.md

**Status:** proposed (spec only; no implementation in this change)
**Build:** [build.NCBI_parse.md](build.NCBI_parse.md) describes the modules as pseudocode. Reading that file does not create Python.

Reading this file does not create Python.

## Scope

Choose one representative FASTA from each group of accessions already written by the NCBI search, record every accession and any failure in `output/accession_criteria.csv`, write the selected sequence table `output/NCBI_representative_seq.csv`, and copy the chosen accession onto the matching row of `output/genes.csv`. The choice is local. This step does not call NCBI.

## Inputs

| Input | Path |
| --- | --- |
| Query table | `output/genes.csv` |
| Accession table | `output/accessions.csv` |
| FASTA files | `output/clinical_genes/{Accession}.fasta` |

`output/genes.csv` has the header `Family,Genus,Virus,Human pathogen hazard group,Schedule 5`. It may already have an `Accession` column.

`output/accessions.csv` has the header `Virus,Rank,Accession`. Rows that share the same `Virus` cell are one query group. A group has at most 5 data rows, ranks 1 through 5. The `Virus` cell is the query text.

A FASTA file has one header line, the line that starts with `>`, and a sequence after that line. Part 2 may have skipped a download, so the FASTA file for an accession may be absent. A file that is present but empty, does not start with `>`, or contains a second header line is an input error. It is not a scored row.

## Screened words

1. Take the query text for the group.
2. Delete each complete square-bracket tag: the opening `[`, all text inside it, and the closing `]`. No bracket character remains. For example, `[organism]`, `[title]`, and `[SLEN]` are removed in full. Words outside the brackets stay, including the word `virus`.
3. Split the remaining text into alphanumeric words on every character that is not an ASCII letter or digit (`[^A-Za-z0-9]+`).
4. Lowercase each word. Drop empty words. Keep first-seen order and drop duplicates.

`human[organism] mitochondrion genome` deletes the complete substring `[organism]`, including `[` and `]`, and yields:

1. `human`
2. `mitochondrion`
3. `genome`

`virus[organism]` deletes `[organism]` and keeps `virus`.

The specific search term is those screened words joined by single spaces: `human mitochondrion genome`. For `human insulin`, the specific search term is `human insulin`.

If no screened words remain, every accession in the group is a failure. `Failure` is `no screened words`. `Representative` is `0`.

## Header words

When the FASTA file is present, read its header line. Split that line into alphanumeric words on every character that is not an ASCII letter or digit (`[^A-Za-z0-9]+`). Compare case-insensitively, whole alphanumeric word to whole alphanumeric word.

Worked header:

```text
>OZ567094.1 Homo sapiens genome assembly, organelle: mitochondrion
```

The screened words are `human`, `mitochondrion`, and `genome`. `genome` and `mitochondrion` appear in the header. `human` does not match `Homo`. The word-match count is 2 (`mitochondrion;genome`).

## Selection priority

The sequence is every character after the header line, through the end of the file, with whitespace removed. The header line, including the leading `>`, is not part of the length. `GeneLength` is that count in bp.

A FASTA longer than 40,000 bp is not a candidate. A length of 40,000 bp is allowed.

A missing FASTA file is not a candidate.

Rank the remaining FASTA files by these rules, in this order:

1. **Words in order, highest priority.** The screened words appear in the header in the same order. Other header words may sit between them. If one or more files have this in-order match, only those files remain candidates.
2. **Words adjacent, next.** Among the files still in play, prefer those where the screened words also sit next to each other, in that order, with no header word between them. Adjacent is the tighter form of the same order. It breaks ties among in-order matches. If no file is in order, none can be adjacent, and selection continues at rule 3.
3. **Highest word match.** When no file has the screened words in order, count how many distinct screened words appear in the header. Keep only the files with the highest count. A count of 0 is not a candidate.
4. **Lowest match-continuation penalty.** Among the files still tied, prefer the header that extends each matched word the least. For every matched word, find each case-insensitive whole-word occurrence in the original header. After that occurrence, count alphanumeric words until the end of the header or one of `,`, `;`, `:`, `(`, `)`, `[`, `]`, or `/`. Repeated occurrences of one word keep the lowest count. Add those counts. The sum is `MatchContinuationPenalty`. A lower sum is more specific. This rule does not apply when an in-order candidate exists.
5. **Largest gene length.** Among the files still tied, keep the longest sequence at or below 40,000 bp.

If two files are still tied after rule 5, keep the one with the lower `Rank` in `output/accessions.csv`.

## Failure report

`output/accession_criteria.csv` is the failure report. Every accession from `output/accessions.csv` gets one row, including a missing FASTA and a group that produces no representative.

`Failure` is empty when the row was scored and could be chosen. `Representative` is `1` only for the chosen row. A row that was scored but not chosen has an empty `Failure` and `Representative` `0`.

Set `Failure` to the first reason that applies:

| Failure | When |
| --- | --- |
| `no screened words` | The query has no words left after the bracket tags are deleted |
| `missing fasta` | `output/clinical_genes/{Accession}.fasta` is not a file |
| `longer than 40000 bp` | The sequence is longer than 40,000 bp |
| `no word match` | No screened word appears in the header |

A group whose every row has a `Failure` has no representative. Each of those rows keeps `Representative` `0`.

## Commas

Text written to `output/accession_criteria.csv` escapes a backslash as `\\` and a comma as `\,`. The header `mitochondrion, complete sequence` is written `mitochondrion\, complete sequence`. The escape keeps `Header` in one column so `Representative` stays the last column.

## Outputs

### 1. `output/accession_criteria.csv`

One row per accession, in the same order as `output/accessions.csv`.

```csv
Query,Rank,Accession,ScreenedWords,InOrderMatch,AdjacentMatch,WordMatchCount,MatchedWords,MatchContinuationPenalty,GeneLength,WithinUpperCutoff,Header,Failure,Representative
```

| Column | Value |
| --- | --- |
| `Query` | The `Virus` cell from `output/accessions.csv`, unchanged |
| `Rank` | The 1-based rank from `output/accessions.csv` |
| `Accession` | The accession from `output/accessions.csv` |
| `ScreenedWords` | The screened alphanumeric query words joined by `;` |
| `InOrderMatch` | `1` when the screened words appear in the header in that order, other words allowed between them; else `0` |
| `AdjacentMatch` | `1` when those words also appear next to each other in that order; else `0` |
| `WordMatchCount` | Count of distinct screened words found in the header |
| `MatchedWords` | Those matched words in screened order, joined by `;` |
| `MatchContinuationPenalty` | Sum of the shortest continuation counts for the matched words. Empty when the FASTA file is missing. `0` when no screened word matched |
| `GeneLength` | Sequence length in bp after the header line. Empty when the FASTA file is missing |
| `WithinUpperCutoff` | `1` when `GeneLength` is present and `GeneLength <= 40000`; else `0` |
| `Header` | The FASTA header line without the leading `>`, with commas escaped. Empty when the FASTA file is missing |
| `Failure` | The failure reason from the table above, or empty |
| `Representative` | Last column. `1` if this sequence was chosen for the query group, else `0` |

### 2. `output/NCBI_representative_seq.csv`

One data row for each query group that has a chosen sequence. A group with no chosen sequence is absent here; its failure reasons are in `output/accession_criteria.csv`.

```csv
Query,Accession,GeneLength,Sequence,Representative
```

| Column | Value |
| --- | --- |
| `Query` | The `Virus` cell for that group, unchanged |
| `Accession` | The accession of the selected FASTA, without `.fasta` |
| `GeneLength` | Sequence length in bp after the header line |
| `Sequence` | The sequence residues only, whitespace removed, with no header and no leading `>` |
| `Representative` | `1`. Every row in this file is a chosen sequence |

### 3. `output/genes.csv`

`output/genes.csv` is the list of queries. `output/accession_criteria.csv` is the list of scored accessions. They meet on the query text: the `Virus` cell in `genes.csv` and the `Query` cell in the criteria file.

For each data row in `genes.csv`, find the criteria row with the same query text and `Representative` `1`. The same query text means both cells are equal after spaces at the two ends are removed. Write that row's `Accession` onto the `genes.csv` row.

- If `genes.csv` has no `Accession` column, add one at the end.
- If `genes.csv` already has an `Accession` column, fill that column. Do not add a second one.
- If two `genes.csv` rows have the same `Virus` text, each receives the same accession.
- If that query has no `Representative` `1` row, leave `Accession` empty. The reason is in `Failure` on the criteria rows for that query.

The other columns stay as they are, in their existing order. Row order stays as it is.

Write the updated `genes.csv` atomically:

1. Write the complete updated table to a uniquely named temporary file in `output/`.
2. Flush and close the temporary file.
3. Replace `output/genes.csv` with the temporary file using one atomic filesystem replacement.
4. Do not open `output/genes.csv` for in-place writing.
5. If reading, writing, flushing, closing, or replacing fails, delete the temporary file when possible and leave the previous `output/genes.csv` unchanged.

The same atomic-write rule applies whether `Accession` is newly appended or an existing `Accession` column is updated.

```csv
Family,Genus,Virus,Human pathogen hazard group,Schedule 5,Accession
,,human[organism] mitochondrion genome,,,OZ560341.1
,,human insulin,,,NG_008849.1
```
