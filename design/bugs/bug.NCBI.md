# bug.NCBI. Field flags were sent inside quotes

Date: 2026-10-17  
Status: fixed

## Defect

`EntrezTermComposer` wrapped the whole `Virus` cell in one pair of quotes. A field flag in that cell, including `[organism]`, sat inside the quotes. NCBI treated the flag as literal text.

The cell `human[organism] mitochondrion genome` was sent as:

```text
"human[organism] mitochondrion genome" AND gene AND 8001:999999999[SLEN]
```

That search returned 0 hits. The same words on the NCBI website, with `[organism]` outside quotes, returned results. `output/accessions.csv` then contained only the `human insulin` row.

## Required behavior

Quote the value that belongs to a field. Place the field flag after the closing quote.

`human[organism] mitochondrion genome` is sent as:

```text
"human"[organism] mitochondrion genome
```

`[organism]` is not inside the quotes. Free text that is not bound to a field stays outside those quotes. `search.txt` and the `[SLEN]` clause are not appended to a cell that contains a field flag, and they are not placed inside the quotes.

A cell with no field flag is still sent as `"{cell}" AND {extra} AND {bp + 1}:{MAX_SLEN}[SLEN]`.

## Correction

`EntrezTermComposer.compose` in `src/virus_redteaming/clinical_fasta/term.py`.
