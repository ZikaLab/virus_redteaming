# 0002. Parse the Approved List virus tables via pdfplumber

Date: 2026-10-14  
Status: accepted

## Context

`misc208.pdf` stores the virus catalogue as three-column tables from printed page 27. Plain text extraction concatenates columns and merges notes onto the next agent name.

## Decision

Extract tables with pdfplumber behind a `TableExtractor` protocol. Parse Family/Genus as sticky context. Write long-format CSV. Tests use in-memory table rows so CI does not require the PDF binary.

## Consequences

The only PDF-library type is the adapter. Spot-check fixtures encode the Hantaviridae and Flaviviridae rows from `design/specs/spec.redteam.md`.
