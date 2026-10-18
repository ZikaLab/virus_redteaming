# 0004. Category 1 joins ICTV and viruses.csv on Genus

Date: 2026-10-18  
Status: accepted

## Context

`output/viruses.csv` and `docs/ICTV_RNA_virus_species_MSL41.csv` share the taxonomic key `Genus`. Joining on `Family` fails when ICTV reorganizes families while keeping the genus intact (for example, `Orbivirus`, `Rotavirus`, `Orthoreovirus`, `Coltivirus`, and `Seadornavirus` under `Reoviridae` vs. `Sedoreoviridae`/`Spinareoviridae`, and `Pegivirus` under `Flaviviridae` vs. `Hepaciviridae`). Within a matched `Genus`, `Virus` in `viruses.csv` and `Exemplar virus` in ICTV often differ in spelling or serotype detail.

## Decision

1. The taxonomic key is `Genus`. Catalogue genus strings that differ from the ICTV genus of the same taxon are harmonized semantically to `NEN genus`, an exact ICTV `Genus`.
2. Within `NEN genus`, harmonize `Virus` to one or more `Exemplar virus` strings (`NEN virus`, including serotypes) in `output/nen_viruses.csv`.
3. Run `EXCEPT` inside `NEN genus`, then sample Category 1 rows into `output/ICTV_cat1.csv` with `Human pathogen hazard group` = `1` and `Schedule 5` = `0`.
4. Genera belonging to DNA and reverse-transcribing viruses are recorded in `design/non-RNA_viruses.md`. Their `NEN genus` is empty.

## Consequences

Exact genus matches are copied into `NEN genus`, and the virus prompt runs in that genus. A virus prompt that finds nothing retries the genus prompt, which is how the Sapporo row moves from `Norovirus` to `Sapovirus`. `Ortonairovirus` resolves to `Orthonairovirus`, `Hepacivirus` to `Orthohepacivirus`, and the blank Astroviridae catch-all to `Mamastrovirus`. Genus-prompt candidates are the ICTV genera of the catalogue family, plus a stem match when the taxon has moved family. The sample size is the number of catalogue rows that share an `NEN genus`. A genus that is not in the RNA table is not paired with an RNA genus.
