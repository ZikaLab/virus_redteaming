# bug.NCBI_parse. The representative file omits the insulin gene

Date: 2026-10-17  
Status: fixed

## Correction

`HeaderMatch.continuation_penalty` measures how far each matched word continues before a clause boundary. When no row is in order, `RepresentativeSelection.choose` uses the lowest penalty before gene length. `NG_007114.1` now wins `human insulin`, and `OZ560341.1` still wins the tied mitochondrion headers. `MatchContinuationPenalty` is a column in `output/accession_criteria.csv`. The representative writer is unchanged.

## Problem

`output/accession_criteria.csv` is correct. `output/NCBI_representative_seq.csv` is not. The insulin gene is omitted from the representative file.

The query is `human insulin`. The criteria table scores all five accessions and marks `NG_008849.1` as `Representative` 1. The insulin gene in that group is `NG_007114.1`. Its criteria row is present, its `Failure` is empty, and its `Representative` is 0. The representative file therefore never receives it.

The second row of `output/NCBI_representative_seq.csv` is not missing. It is the wrong sequence. `csv.reader` returns:

| Query | Accession | GeneLength | What the header says |
| --- | --- | --- | --- |
| `human[organism] mitochondrion genome` | `OZ560341.1` | 16572 | Homo sapiens mitochondrion |
| `human insulin` | `NG_008849.1` | 27487 | insulin like growth factor 2 (IGF2) |

`NG_007114.1`, header `Homo sapiens insulin (INS), RefSeqGene on chromosome 11`, length 8416, is not in that file.

## Root cause

This is a selection bug. The representative writer is doing what the criteria flags tell it to do.

`AtomicRepresentativeSink` writes only rows whose `Representative` flag is 1. For this run that flag is 1 on `OZ560341.1` and `NG_008849.1`. Both rows are in `output/NCBI_representative_seq.csv`. The sink did not drop a chosen row.

`human insulin` is screened to `human`, `insulin`. Every header in the group says `Homo`, not `human`, so `human` matches nothing. In-order match is 0 for every row. Adjacent match is 0 for every row. Selection therefore falls through to word count.

Four headers contain the whole word `insulin`:

| Rank | Accession | Length | Header gene | Word count | Failure | Representative |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `NM_001079817.3` | 9427 | insulin receptor (INSR), mRNA | 1 | empty | 0 |
| 2 | `NG_008852.2` | 188746 | insulin receptor (INSR), RefSeqGene | 1 | `longer than 40000 bp` | 0 |
| 3 | `NG_008849.1` | 27487 | insulin like growth factor 2 (IGF2) | 1 | empty | 1 |
| 4 | `NG_007114.1` | 8416 | insulin (INS) | 1 | empty | 0 |
| 5 | `NC_001144.5` | 1078177 | Saccharomyces cerevisiae chromosome XII | 0 | `longer than 40000 bp` | 0 |

`RepresentativeSelection.choose` keeps the highest word count above 0, then the longest sequence at or below 40,000 bp, then the lower rank. The three eligible rows tie at word count 1. Length then keeps `NG_008849.1` at 27,487 bp. `NG_007114.1` stays eligible, with an empty `Failure` and `Representative` 0, and the writer skips it.

The length rule is why the mitochondrion group is right. Those five headers tie at word count 2, and the longest, `OZ560341.1` at 16,572 bp, wins. Replacing "longest" with "shortest" would select the insulin gene and would also change the mitochondrion winner. That is the wrong fix.

## Proposed fixes

Use a general lexical specificity tie-break. Do not hard-code `insulin`, `INS`, any accession, or a gene-name dictionary.

### Match-continuation penalty

For each distinct screened word that matched:

1. Find every whole-word occurrence in the original header, case-insensitively.
2. Starting immediately after that occurrence, count the alphanumeric words before the next clause boundary.
3. A clause boundary is end of header or one of `,`, `;`, `:`, `(`, `)`, `[`, `]`, or `/`.
4. If the matched word occurs more than once, keep the lowest count for that word.
5. Add those lowest counts. The sum is `MatchContinuationPenalty`. Lower is more specific.

This measures how much the header extends each matched query word before reaching a boundary. It does not penalise accession, organism, or other metadata before the matched word.

Examples:

| Header fragment | Matched word | Continuation | Penalty |
| --- | --- | --- | --- |
| `insulin (INS)` | `insulin` | none before `(` | 0 |
| `insulin receptor (INSR)` | `insulin` | `receptor` | 1 |
| `insulin like growth factor 2 (IGF2)` | `insulin` | `like growth factor 2` | 4 |
| `genome assembly, organelle: mitochondrion` | `genome`; `mitochondrion` | `assembly`; none | 1 |
| `mitochondrion, complete sequence, whole genome shotgun sequence` | `mitochondrion`; `genome` | none; `shotgun sequence` | 2 |

### Revised fallback order

Do not change the full in-order or adjacent rules. Apply this tie-break only in the existing fallback branch where no eligible row contains every screened word in order:

1. highest distinct screened-word match count;
2. lowest `MatchContinuationPenalty`;
3. longest sequence at or below 40,000 bp;
4. lower rank.

For `human insulin`, the three eligible rows still tie at word count 1. Their penalties are 1, 4, and 0, so `NG_007114.1` wins.

For the mitochondrion group, the four assembly headers have penalty 1. They remain tied, so length still selects `OZ560341.1`. The whole-genome-shotgun header has penalty 2 and does not displace them.

### Required implementation

1. Add the calculated penalty to the scored immutable value. `HeaderMatch` owns calculation from the original header and matched words. `RepresentativeSelection` consumes the value; it does not parse header text.
2. Add `MatchContinuationPenalty` to `output/accession_criteria.csv` so every selection criterion remains visible. It is empty for a missing FASTA and `0` when no screened word matched.
3. Update `spec.NCBI_parse.md` and `build.NCBI_parse.md` before changing Python because this inserts a criterion before length.
4. Leave `AtomicRepresentativeSink` unchanged. It must continue writing one row per chosen group.
5. Add regression tests for all examples above, repeated occurrences, case-insensitive whole-word matching, no matched words, and boundaries at end of header and each listed delimiter.
6. Add an end-to-end local parse test with the five current insulin headers. It must choose `NG_007114.1`, while the mitochondrion fixture must still choose `OZ560341.1`.

## Assessment

This rule generalises the observed distinction between an exact short label and a longer compound label without biological aliases. It is still a lexical heuristic, not proof that an accession is the intended biological gene. The criteria column makes that limitation inspectable. If future examples show that punctuation conventions are insufficient, the next design should use structured NCBI annotation fields rather than adding gene-specific exceptions.
