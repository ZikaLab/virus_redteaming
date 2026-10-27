# 0007. FASTA files come from the merged GenBank column

Date: 2026-10-18  
Status: accepted

## Context

`output/HSE-virus_Cat1-virus_merged.csv` has 424 rows: 33 rows with a blank `GenBank accessions` cell and 391 rows containing 771 segment occurrences across 727 distinct accessions. A cell holds either one accession or semicolon-separated genome segments whose label precedes a colon (`RNA1: V00603; RNA2: J02151`).

Three constraints govern downloading these 727 records into `output/NCBI_fasta/`:

1. Regex-only extraction (`re.findall`) would silently ignore a corrupted segment or treat an unparseable non-blank cell as a blank row.
2. Fetching 727 accessions serially over Entrez takes several minutes; re-fetching files that are already on disk after an interrupted run wastes time and quota, while a naive cache check (such as checking only for a leading `>`) would trust a truncated or mismatched FASTA file.
3. All 727 distinct codes resolve in NCBI `nuccore` under the same stem. Versions are `.1` (656), `.2` (64), `.3` (5), `.4` (`AY632536.4`), and `.5` (`AF291704.5`). `efetch` FASTA for `V00603` begins `>V00603.1`. The cell stores the code without a version, and `AccessionIdentity` accepts the versioned header.

## Decision

Add `fetch-ncbi-fasta` (`--csv` defaulting to `output/HSE-virus_Cat1-virus_merged.csv`, `--out` defaulting to `output/NCBI_fasta`):

1. `GenBankSegmentParser` splits non-blank cells on `;`, splits labelled segments on `:`, strips trailing coordinate ranges, and validates every accession token with the `GenBankAccessionParser` pattern. Blank cells are skipped; malformed non-blank cells raise `NcbiFastaInputError`.
2. `DirectoryFastaCache` implements `FastaCache` and treats `{out}/{accession}.fasta` as a cache hit only when `Bio.SeqIO.parse` yields one non-empty FASTA record accepted by `AccessionIdentity.matches(record, accession)`. `NcbiFastaDownload` depends on `FastaCache` rather than reading the filesystem directly.
3. Header checks stay in `FastaFetchSource` and `AccessionIdentity`. A returned `.1` matches the unversioned code from the table, and the file is still named with the requested code. A different header stem raises `NcbiRecordRejected`. Every segment length is kept.

## Consequences

Interrupted runs resume from validated FASTA files already on disk, while corrupted or mismatched files are re-fetched and atomically replaced. `NcbiFastaDownload` depends purely on Protocols. A populated cell that breaks the segment grammar fails before any network call.
