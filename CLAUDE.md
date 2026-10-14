# Claude Code instructions

You are working in **zikalab/virus_redteaming**, an AI/LLM red-teaming research project.

**Follow `constitution/CONSTITUTION.md` as law.** If a request conflicts with it, follow the constitution and say so.

## Must

- OOP Python 3.11+, SOLID, `src/` layout
- Protocols + constructor injection; no god objects
- Design artifacts in `design/` for architectural work
- Tests in `tests/unit` or `tests/integration`
- Typed public APIs; `mypy --strict` quality

## Must not

- Procedural dumps in `scripts/` or notebooks as the real design
- Biological / pathogen / weapon content
- Exploit payloads or attack reproduction steps

When unsure, read the constitution, then the nearest ADR in `design/decisions/`.
