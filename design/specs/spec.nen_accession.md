# spec.nen_accession.md

**Status:** accepted  
**Build:** [build.nen_accession.md](build.nen_accession.md)

## Goal

Copy the NCBI nucleotide accession for each `NEN virus` in `output/nen_viruses.csv` from the matching row of `docs/VMR_MSL41.v1.20260729.csv`.

The source cell is `Virus GENBANK accession`. The value written is the NCBI accession code or codes inside that cell. This step does not call NCBI. It does not download sequence. It does not change any other column.

## Match

Compare `NEN virus` with `Virus name(s)`.

| Rule | Detail |
| --- | --- |
| Cleaning | Replace U+00A0 with a normal space, then strip both ends. |
| Equality | The cleaned strings must be identical, including case and diacritics. |
| Whole cell | A semicolon inside `Virus name(s)` stays part of that one name. A synonym on one side of the semicolon is not a separate match. |
| Blank `NEN virus` | Leave `NCBI accession` empty. Do not treat the blank as an unmatched name. |
| No row | Leave `NCBI accession` empty and report the `NEN virus` text. |

When several VMR rows share the cleaned name, use the first row whose `Exemplar or additional isolate` cell is `E`. When none is `E`, use the first row in file order.

## NCBI accession

Read `Virus GENBANK accession` from the chosen row.

| Kept | Dropped |
| --- | --- |
| GenBank accession, including a version suffix such as `.1` | Segment labels (`L:`, `Seg1:`, `DNA-C:`) |
| RefSeq-style codes such as `NC_001474` when they appear in that cell | Coordinate ranges in parentheses, such as `(1.3949)` |
| Each distinct code once, in the order it first appears | A repeated code |

Join the codes with `; ` (semicolon, space) and write them to a column named `NCBI accession`.

An empty GenBank cell writes an empty `NCBI accession`. That row still counts as matched.

## Columns

`output/nen_viruses.csv` keeps every existing column. `NCBI accession` is inserted immediately after `NEN virus`:

`Family`, `Genus`, `NEN genus`, `Viruses`, `NEN virus`, `NCBI accession`, `Human pathogen hazard group`, `Schedule 5`, `Issues`

`Family`, `Genus`, `NEN genus`, `Viruses`, `NEN virus`, `Human pathogen hazard group`, `Schedule 5`, and `Issues` are copied unchanged. A second run writes the same file.

## Report

The run reports how many rows received a lookup, which non-blank `NEN virus` values had no VMR row, and how many `NEN virus` cells were blank.

## Out of scope

No Entrez search. No FASTA download. No edit to the VMR, to `output/viruses.csv`, or to `output/ICTV_cat1.csv`. No change to the Category 1 sampler.
