# Agent instructions (Cursor and this harness)

This repository is **zikalab/virus_redteaming**.

The binding engineering standard is **`constitution/CONSTITUTION.md`**. Cursor project rules in `.cursor/rules/` repeat the same standard so this harness loads it automatically.

## Defaults

- Language: Python 3.11+, OOP, SOLID
- Package: `src/virus_redteaming`
- Tests: `tests/`
- Design: `design/` (specs, ADRs, diagrams, architecture)
- Quality: ruff + mypy strict + pytest

## Workflow

1. Read the constitution before implementing.
2. For a new boundary or type family, add or update `design/` first.
3. Implement the smallest responsible classes against Protocols.
4. Add tests that exercise the public contract with Protocol fakes.
5. Do not expand a class that already has more than one reason to change.

`CLAUDE.md` is the Claude Code pointer to the same constitution. Do not let those files drift; change the constitution, then the pointers.
