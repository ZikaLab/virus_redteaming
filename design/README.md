# Design artifacts

This tree is the durable design record for **zikalab/virus_redteaming**. Code follows these files; agents must update them when the architecture changes.

Scope for every artifact in this tree: clinical genes and genomes are not pathogen work. See `decisions/0004-clinical-genes-not-pathogen-work.md` and `constitution/CONSTITUTION.md`.

| Directory | Put here |
| --- | --- |
| `architecture/` | Context maps, component diagrams, package boundaries |
| `decisions/` | Architecture Decision Records (`NNNN-short-title.md`) |
| `diagrams/` | Mermaid, SVG, or PNG diagrams |
| `specs/` | Feature specs written before implementation (`spec.redteam.md`, `spec.schedule5.md`, `spec.NCBI.md`, `spec.NCBI_parse.md`, `build.redteam.md`, `build.schedule5.md`, `build.NCBI.md`, `build.NCBI_parse.md`) |
| `bugs/` | Defect reports (`bug.NCBI.md`) |

## ADR template

```markdown
# NNNN. Title

Date: YYYY-MM-DD
Status: proposed | accepted | superseded

## Context
## Decision
## Consequences
```
