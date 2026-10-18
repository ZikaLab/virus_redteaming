# build.nen_accession.md

**Status:** accepted  
**Spec:** [spec.nen_accession.md](spec.nen_accession.md)

Package: `src/virus_redteaming/nen_accession/`. The CLI in `src/virus_redteaming/__main__.py` only builds the object graph.

## Types

| Type | Job |
| --- | --- |
| `VmrIsolate` | One VMR row: cleaned virus name, whether it is the exemplar, raw GenBank cell. |
| `NenVirusRecord` | One nen row. `with_ncbi` returns a new record. |
| `AssignmentReport` | Matched rows, unmatched names in file order, blank `NEN virus` count. |
| `GenBankAccessionParser` | Extracts accession codes from one GenBank cell. |
| `ExemplarVirusIndex` | Maps a cleaned virus name to the chosen `VmrIsolate`. |
| `NenAccessionAssigner` | Applies the index and parser to nen records. |
| `VmrCsvReader` | Reads the VMR CSV into `VmrIsolate` values. |
| `NenCsvReader` | Reads nen CSV into `NenVirusRecord` values. |
| `NenAccessionWriter` | Writes the nine-column nen CSV. |
| `AssignNenAccessions` | Reads both files, assigns, writes the nen path, returns the report. |

Readers and the writer are separate from the assigner. The assigner depends on `VirusIndex` and `AccessionParser` protocols. The workflow receives the readers, the writer, the parser, and an index factory through its constructor.

## Accession pattern

Try these alternatives in this order, then an optional `.` and digits:

1. Two letters, underscore, 6 to 9 digits.
2. Two letters and 8 digits.
3. Two letters and 6 digits.
4. One letter and 5 digits.

## Errors

`NenTableError` when the nen header lacks a required column. `VmrTableError` when the VMR header lacks `Virus name(s)`, `Exemplar or additional isolate`, or `Virus GENBANK accession`. Both subclass `VirusRedteamingError`.

## CLI

```text
virus_redteaming assign-nen-accessions \
  --nen output/nen_viruses.csv \
  --vmr docs/VMR_MSL41.v1.20260729.csv
```

Print the matched count, each unmatched `NEN virus`, and the blank count.

## Tests

Unit tests cover the parser, the exemplar choice, the assigner, and the CSV adapters, using temporary files and in-memory records. An integration test runs `AssignNenAccessions` on a temporary nen file and the repository VMR, and checks dengue types, a multi-segment exemplar, a name with no exemplar, a missing name, and a blank `NEN virus`.
