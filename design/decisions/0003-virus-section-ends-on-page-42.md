# 0003. Virus tables end on printed page 42

Date: 2026-10-14  
Status: accepted

## Context

The first extractor sliced `pdf.pages[26:]` (printed page 27 through EOF). Page 43 is Annex 1, not the catalogue. The spec now requires pages 27–42 only.

## Decision

A `PrintedPageWindow(27, 42)` plus `AnnexTitleHaltPolicy` drive `VirusSectionPageSelector`. The PDF adapter breaks the page loop on `HALT` once past page 26. Default CSV path is `output/viruses.csv`.

## Consequences

Annex 1 and its second `Viruses` heading never enter the row stream. Changing bounds later means editing the window value object, not the parser.
