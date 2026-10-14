# virus_redteaming Constitution

**Status:** active  
**Applies to:** every contributor and every coding agent (Claude Code, Cursor, and this harness)  
**Canonical copy:** this file. Other agent files only point here.

This project is an **AI/LLM red-teaming** research codebase. It is **not** a biological, chemical, or weapons project. Do not add pathogen, synthesis, or exploit-payload content.

## I. Non-negotiables

1. Write **typed, object-oriented Python 3.11+** in a `src/` layout.
2. Apply **SOLID** on every new type. Prefer Protocols and composition over inheritance.
3. Put production code in `src/virus_redteaming/`. Put tests next to behavior in `tests/`.
4. Record non-trivial design in `design/` **before** large implementation.
5. Do not place business rules in scripts, notebooks, `__init__.py`, or test files.
6. Do not introduce god objects, service locators, or untyped `dict` bags as domain models.
7. Public APIs are explicit classes or functions with type annotations. No implicit globals.

## II. SOLID in this codebase

### S — Single Responsibility

- One class has one reason to change.
- Split orchestration, IO, parsing, scoring, and persistence into different types.
- If a class name needs "And" or "Manager", split it.

```python
# BAD: one class loads, scores, and writes
class RunManager:
    def run(self, path: str) -> None: ...

# GOOD: three types, one job each
class PromptLoader: ...
class Scorer: ...
class ResultWriter: ...
```

### O — Open/Closed

- Extend by adding types, not by editing `if/elif` ladders on closed modules.
- New behaviors implement a Protocol. Callers depend on the Protocol.

```python
class Scorer(Protocol):
    def score(self, output: str) -> float: ...

class LengthScorer:
    def score(self, output: str) -> float:
        return float(len(output))
```

### L — Liskov Substitution

- Subtypes must honor the Protocol contract: same preconditions, no stronger exceptions, no no-op stubs.
- Do not inherit only to reuse helpers. Extract a collaborator instead.

### I — Interface Segregation

- Prefer small Protocols (`Loader`, `Scorer`, `Sink`) over one mega-interface.
- Callers must not depend on methods they do not use.

### D — Dependency Inversion

- High-level policy depends on Protocols, never on concrete IO libraries.
- Inject collaborators through `__init__`. Do not import concretes inside methods to "new up" graph nodes.

```python
class EvaluationRun:
    def __init__(self, loader: PromptLoader, scorer: Scorer, sink: ResultSink) -> None:
        self._loader = loader
        self._scorer = scorer
        self._sink = sink
```

## III. OOP conventions

- **Composition over inheritance.** Inheritance only for true is-a types that share a contract.
- **Protocols** (`typing.Protocol`) for seams. ABC only when you must enforce a base at runtime.
- **Dataclasses** (frozen when values are immutable) for data. Behavior lives on dedicated types.
- **No anemic domain with logic in "utils".** Helpers are methods on the type that owns the rule, or a well-named collaborator.
- **Errors:** custom exception types in `core/errors.py` (or a bounded-context errors module). Do not raise bare `Exception`.
- **Names:** classes `PascalCase`, modules `snake_case`, constants `UPPER_SNAKE`. One public class per module unless a tight cluster belongs together.
- **Typing:** every public function and method is fully annotated. `mypy --strict` is the bar.
- **Immutability:** prefer frozen dataclasses and return new values rather than mutating shared state.

## IV. Layout and ownership

| Path | Owns |
| --- | --- |
| `src/virus_redteaming/core/` | Shared contracts, errors, value objects |
| `src/virus_redteaming/<context>/` | One bounded context per package |
| `tests/unit/` | Fast tests; no network, no real filesystem unless tmp_path |
| `tests/integration/` | Collaborator wiring and IO adapters |
| `design/architecture/` | System shape, context maps |
| `design/decisions/` | ADRs (`NNNN-title.md`) |
| `design/diagrams/` | Sequence/class diagrams (Mermaid or SVG) |
| `design/specs/` | Feature specs before implementation |
| `scripts/` | Thin CLI entrypoints that assemble the object graph |

New bounded contexts get their own package plus matching `tests/unit/<context>/`.

## V. Design artifacts

Before a feature that adds a type family, a new IO boundary, or a scoring policy:

1. Write or update a spec in `design/specs/`.
2. If the decision is lasting, add an ADR in `design/decisions/`.
3. Keep diagrams in `design/diagrams/` in sync with the code you ship.

Agents must not skip this for "small" architectural changes. Trivial bugfixes do not need an ADR.

## VI. Testing

- Every new public type has unit tests.
- Tests name the behavior, not the implementation (`test_scorer_rejects_empty_output`).
- Use fakes that implement Protocols. Do not mock every method of a concrete class.
- Do not test private helpers in isolation if the public contract already covers them.

## VII. Agent operating rules (Claude, Cursor, this harness)

1. Read this constitution at the start of implementation work.
2. Propose types and Protocols before writing large function bodies.
3. Refuse to add procedural scripts that bypass the object model.
4. Keep changes in the smallest responsible types; do not "just add a method" to a crowded class.
5. Match existing package style. Do not introduce a second architecture.
6. After code changes, run `ruff`, `mypy`, and `pytest` when the environment allows it.
7. Never commit secrets. Never weaken `.gitignore` to include `.env` files.

## VIII. Amendments

Amendments are ADRs that update this file in the same change. Do not contradict this file in `CLAUDE.md`, `AGENTS.md`, or `.cursor/rules/`; those files must defer here.
