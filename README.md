# virus_redteaming

Python research project for **AI/LLM red-teaming**. The codebase is a from-scratch OOP layout that follows SOLID. It is not a biology or pathogen project.

Organization: **zikalab**  
Repository: **virus_redteaming**

## Layout

```
src/virus_redteaming/   importable package (src layout)
tests/unit/             fast, isolated tests
tests/integration/      cross-module / IO tests
design/                 design artifacts (ADRs, architecture, diagrams, specs)
output/                 generated CSV (viruses.csv)
constitution/           non-negotiable engineering constitution
docs/                   source PDFs for parse-viruses (misc208.pdf)
scripts/                operator scripts (no business logic)
```

## Requirements

- Python 3.11+
- Agents (Claude Code and Cursor) must follow `constitution/CONSTITUTION.md`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

## Approved List virus CSV

Design: `design/specs/spec.redteam.md`  
Build: `design/specs/build.redteam.md`

```bash
python -m virus_redteaming parse-viruses
```

Reads **`docs/misc208.pdf`** and writes **`output/viruses.csv`**. Parses the **Viruses** tables on printed pages **27–42** of the HSE Approved List. It does not provide laboratory guidance.

## Agent entry points

| Harness | File |
| --- | --- |
| Claude Code | `CLAUDE.md` |
| Cursor / this session | `AGENTS.md` and `.cursor/rules/` |
| Canonical rules | `constitution/CONSTITUTION.md` |
