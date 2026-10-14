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
constitution/           non-negotiable engineering constitution
docs/                   human-facing notes
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

## Agent entry points

| Harness | File |
| --- | --- |
| Claude Code | `CLAUDE.md` |
| Cursor / this session | `AGENTS.md` and `.cursor/rules/` |
| Canonical rules | `constitution/CONSTITUTION.md` |
