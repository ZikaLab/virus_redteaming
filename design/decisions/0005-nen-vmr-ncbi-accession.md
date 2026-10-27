# 0005. NCBI accession on nen rows comes from the VMR exemplar

Date: 2026-10-18  
Status: accepted

## Context

`output/nen_viruses.csv` names each catalogue virus in `NEN virus`. The Virus Metadata Resource `docs/VMR_MSL41.v1.20260729.csv` stores the GenBank nucleotide accession for that name in `Virus GENBANK accession`. Some names occur on more than one VMR row, and the cell often prefixes each accession with a segment label or a coordinate range.

## Decision

Match the cleaned `NEN virus` string to the whole `Virus name(s)` cell. When several rows share that name, take the first exemplar (`E`); otherwise take the first row. Write the extracted NCBI accession codes to a new `NCBI accession` column and leave every other nen column unchanged. Do not call NCBI.

## Consequences

Names absent from the VMR, including `human bocavirus 3` and `human bocavirus 4`, keep an empty `NCBI accession` and are reported. The Category 1 sampler does not read this column. A later `NenWriter` run that uses the six-column Category 1 header would drop it.
