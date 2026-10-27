# spec.hse_cat1_merge.md

**Status:** accepted

## Goal

Write `output/HSE-virus_Cat1-virus_merged.csv` by stacking `output/nen_viruses.csv` and `output/ICTV_cat1.csv`. Every input row is kept. HSE rows come first, in their current order, then Category 1 rows, in their current order.

The tables are not joined on virus name. No `Exemplar virus` is a `NEN virus`.

## Columns

| Column | HSE row | Category 1 row |
| --- | --- | --- |
| Source | `HSE` | `Cat1` |
| Catalogue family | Family | blank |
| Catalogue genus | Genus | blank |
| Catalogue virus | Viruses | blank |
| ICTV family | VMR Family for `NEN virus`, otherwise blank | Family |
| ICTV genus | NEN genus | Genus |
| ICTV virus | NEN virus | Exemplar virus |
| Species | VMR Species for `NEN virus`, otherwise blank | Species |
| Kingdom | VMR Kingdom for `NEN virus`, otherwise blank | Kingdom |
| GenBank accessions | raw VMR `Virus GENBANK accession`, otherwise blank | GenBank accessions |
| NCBI accession | NCBI accession | accession codes parsed from GenBank accessions |
| RefSeq accessions | blank | RefSeq accessions |
| Human pathogen hazard group | copied | copied |
| Schedule 5 | copied | copied |
| Issues | copied | copied |

## VMR lookup

Match the cleaned `NEN virus` to the whole `Virus name(s)` cell. Cleaning replaces U+00A0 with a space and strips both ends. The comparison is case-sensitive. When several rows share the name, use the first exemplar (`E`); otherwise the first row. A blank `NEN virus` is not looked up. `ICTV genus` still comes from `NEN genus` when the VMR has no row.

## Published order

The merge still builds the stack above. The file written to `output/HSE-virus_Cat1-virus_merged.csv` is that stack sorted by:

1. `ICTV genus`, ascending, using the stored string. A blank genus comes before any letter.
2. `Human pathogen hazard group`, descending through `4`, `3*`, `3`, `2`, `1`.
3. `Schedule 5`, descending through `1`, `0`.

Rows that share all three values keep their order in the unsorted stack. A hazard group or Schedule 5 value outside those lists is an error.
