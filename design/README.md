# Design artifacts

This tree is the durable design record for **zikalab/virus_redteaming**. Code follows these files; agents must update them when the architecture changes.

| Directory | Put here |
| --- | --- |
| `architecture/` | Context maps, component diagrams, package boundaries |
| `decisions/` | Architecture Decision Records (`NNNN-short-title.md`) |
| `diagrams/` | Mermaid, SVG, or PNG diagrams |
| `specs/` | Feature specs written before implementation (`spec.redteam.md`, `spec.schedule5.md`, `spec.cat1.md`, `spec.NCBI.md`, `spec.NCBI_parse.md`, `spec.nen_accession.md`, `spec.hse_cat1_merge.md`, `build.redteam.md`, `build.schedule5.md`, `build.cat1.md`, `build.NCBI.md`, `build.NCBI_parse.md`, `build.nen_accession.md`) |
| `bugs/` | Defect reports (`bug.NCBI.md`) |

`non-RNA_viruses.md` lists the HSE virus families whose names are absent from `docs/ICTV_RNA_virus_species_MSL41.csv`. Category 1 does not invent species for those families. Rules: `specs/spec.cat1.md`.

## ADR template

```markdown
# NNNN. Title

Date: YYYY-MM-DD
Status: proposed | accepted | superseded

## Context
## Decision
## Consequences
```
