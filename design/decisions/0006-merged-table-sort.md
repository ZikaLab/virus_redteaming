# 0006. Published merge is sorted by genus, hazard, and Schedule 5

Date: 2026-10-18  
Status: accepted

## Context

`output/HSE-virus_Cat1-virus_merged.csv` stacks every HSE row and then every Category 1 row. That stack is the record of the merge. Reading the published table needs a different order: ICTV genus from A to Z, then human pathogen hazard group from 4 down to 1, then Schedule 5 from 1 down to 0.

## Decision

Sort the merged rows after the stack is built. The sort key is the raw `ICTV genus` ascending, then hazard group in the order `4`, `3*`, `3`, `2`, `1`, then Schedule 5 in the order `1`, `0`, then the row's position in the unsorted stack. Hazard group `3*` stays between 4 and 3. A blank genus sorts before any named genus. Values outside those two lists raise `MergeSortError`.

## Consequences

Re-running `merge-hse-cat1` rewrites the published file in this order. Tests of the merge check that every source row is present. Tests of the order check the key itself.
