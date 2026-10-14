# 0001. Record architecture decisions

Date: 2026-10-14  
Status: accepted

## Context

The project is starting from scratch. Agents and humans need a single place to record why the object model looks the way it does.

## Decision

Use `design/decisions/` for ADRs, numbered sequentially. The engineering constitution in `constitution/CONSTITUTION.md` stays the non-negotiable standard; ADRs explain specific choices that the constitution does not already mandate.

## Consequences

New bounded contexts, IO adapters, and scoring policies get an ADR when they are lasting. Trivial bugfixes do not.
