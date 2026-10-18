# spec.schedule5.md

**Status:** accepted (spec only; no implementation in this change)  
**Depends on:** [spec.redteam.md](spec.redteam.md) (CSV already produced)  
**Build:** [build.schedule5.md](build.schedule5.md)  
**Sources:** `docs/schedule5.md` (46 names), `output/viruses.csv` (232 rows)  
**Inventory (not joined):** `docs/ICTV_RNA_virus_species_MSL41.csv` (7230 rows)  
**Non-scope:** laboratory methods, acquisition, culture, or operational use of listed agents. This workflow only flags name overlap between two published lists. Clinical genes and genomes are not pathogen work (ADR 0004).

## 1. Goal

After `parse-viruses` has written `output/viruses.csv`, annotate the terminal column **Schedule 5** by intersecting `docs/schedule5.md` with the **Virus** column.

| If | Write in Schedule 5 |
| --- | --- |
| The Virus cell **interacts** with at least one name on `docs/schedule5.md` | `1` |
| It does not | `0` |

Do not leave the column blank. Do not write `§`. Do not add or delete CSV rows. Do not change Family, Genus, Virus, or Human pathogen hazard group.

## 2. Inputs

### 2.1 `docs/schedule5.md`

A markdown bullet list. Each line after stripping a leading `- ` is one **schedule-5 name**. Current list (**46** names):

Chikungunya virus; Congo-crimean haemorrhagic fever virus; Dengue fever virus; Dobrava/Belgrade virus; Eastern equine encephalitis virus; Ebola virus; Everglades virus; Getah virus; Guanarito virus; Hantaan virus; Hendra virus (Equine morbillivirus); Herpes simiae (B virus); Influenza viruses (pandemic strains); Japanese encephalitis virus; Junin virus; Kyasanur Forest virus; Lassa fever virus; Louping ill virus; Lymphocytic choriomeningitis virus; Machupo virus; Marburg virus; Mayaro virus; Middleburg virus; Mobala virus; Monkey pox virus; Mucambo virus; Murray Valley encephalitis virus; Ndumu virus; Nipah virus; Omsk haemorrhagic fever virus; Polio virus; Powassan virus; Rabies virus; Rift Valley fever virus; Rocio virus; Sabia virus; Sagiyama virus; SARS Coronavirus; Sin Nombre virus; St Louis encephalitis virus; Tick-borne encephalitis virus (Russian Spring-Summer encephalitis virus); Variola virus; Venezuelan equine encephalitis virus; Western equine encephalitis virus; West Nile fever virus; Yellow fever virus.

Ignore blank lines. Ignore markdown other than `- ` bullets if any appears later.

### 2.2 `output/viruses.csv`

Long-format catalogue from printed pages 27–42. The join key is the **Virus** column only. Family and Genus are not used for matching.

The written header today is `schedule 5`. The required terminal header for this annotation is **`Schedule 5`**. The annotator must write that header (quoted if the CSV dialect requires it). All other header names stay as in the parse spec.

## 3. Interaction (match)

A Virus cell **interacts** with a schedule-5 name when any of the following is true after **normalisation**:

1. **Exact.** Normalised Virus equals normalised schedule-5 name.  
2. **Contained.** Normalised schedule-5 name is a substring of normalised Virus, or the reverse, with length ≥ 6 (avoid matching bare `virus`).  
3. **Alias.** Virus contains `also known as`, `formerly known as`, or `formerly` plus a parenthetical; the alias text matches the schedule-5 name under (1) or (2).  
4. **Recorded synonym.** The pair is in the synonym table in §3.2.

Normalisation (both sides, in order):

1. Unicode NFKC.  
2. Casefold.  
3. Map `á`/`é`/… to ASCII where a single letter remains (`sabiá` → `sabia`).  
4. Replace `/`, `_`, and en/em dashes with space or hyphen consistently (treat `-`, `–`, `/` as equivalent separators).  
5. Collapse whitespace.  
6. Strip a single wrapping pair of parentheses only when the whole string is wrapped.

Do **not** strip the word `virus` globally (`West Nile fever virus` vs `West Nile` would over-match).

### 3.1 Catch-alls

| schedule5.md | Interacts with |
| --- | --- |
| `Ebola virus` | Every Virus whose normalised text contains `ebola` (Bundibugyo, Reston, Sudan, Tai Forest, Zaire ebolavirus) |
| `Polio virus` | `Poliovirus 1`, `Poliovirus 2`, `Poliovirus 3` (and the same names with Human enterovirus C type N) |
| `Influenza viruses (pandemic strains)` | Only Virus cells that are pandemic / HG-elevated influenza A strains in the catalogue, **not** seasonal Influenza B/C/D. If the Virus text does not state pandemic or a listed high-consequence influenza A, do **not** mark `1`. |
| `Tick-borne encephalitis virus (Russian Spring-Summer encephalitis virus)` | Far Eastern tick-borne encephalitis virus and any Virus that names Russian spring–summer encephalitis |
| `SARS Coronavirus` | SARS-CoV-1. Do **not** mark SARS-CoV-2 unless the schedule 5 list is later updated to name it. |

### 3.2 Synonym table (this edition)

Pairs that must count as a match even if naive substring is weak:

| schedule5.md | Virus column (examples in current CSV) |
| --- | --- |
| Junin virus | Argentinian mammarenavirus (also known as Junin virus) |
| Sabia virus | Brazilian mammarenavirus (also known as Sabiá virus) |
| Dengue fever virus | Dengue virus |
| Lassa fever virus | Lassa virus |
| Kyasanur Forest virus | Kyasanur Forest disease virus |
| Congo-crimean haemorrhagic fever virus | Crimean-Congo haemorrhagic fever virus |
| Dobrava/Belgrade virus | Dobrava-Belgrade virus (formerly known as Belgrade (Dobrava) virus) |
| Hendra virus (Equine morbillivirus) | Hendra virus |
| Herpes simiae (B virus) | Herpes B virus also known as Macacine alphaherpesvirus 1 (formerly Herpesvirus simiae) |
| Monkey pox virus | Mpox virus (formerly known as Monkeypox virus) |
| Middleburg virus | Middelburg virus |
| Variola virus | Variola virus (major and minor) |
| Lymphocytic choriomeningitis virus | Both LCMV Armstrong and non-Armstrong rows |

### 3.3 Non-matches

- Catch-all Virus rows (`Other … known to be pathogenic in humans`, `spp.`) do **not** inherit `1` unless the schedule-5 name itself is that catch-all.  
- A match on Family or Genus alone is not an interaction.  
- Unmatched names on `schedule5.md` do **not** create new CSV rows. They are listed in a sidecar report `output/schedule5_unmatched.txt` (one name per line) so gaps are visible.

## 4. Output

In-place update of `output/viruses.csv` (or write then replace; same path).

- Row count unchanged.  
- Column **Schedule 5** is `1` or `0` on every data row.  
- Encoding UTF-8.  
- Human pathogen hazard group, including `*`, is untouched.

Spot checks (Virus → Schedule 5):

| Virus | Schedule 5 |
| --- | --- |
| Andes virus | `0` |
| Dengue virus | `1` |
| Louping ill virus | `1` |
| Yellow fever virus | `1` |
| Zika virus | `0` |
| Guanarito virus | `1` |
| Zaire ebolavirus | `1` |
| Adenoviridae spp. known to be pathogenic in humans | `0` |

## 5. Workflow (after parse)

1. Read `docs/schedule5.md` → set of schedule-5 names.  
2. Read `output/viruses.csv`.  
3. For each data row, test interaction of Virus against the set.  
4. Write Schedule 5 = `1` or `0`.  
5. Write unmatched schedule-5 names to `output/schedule5_unmatched.txt`.

CLI shape (not implemented here):

```bash
python -m virus_redteaming annotate-schedule-5
```

Defaults: `--list docs/schedule5.md`, `--csv output/viruses.csv`.

## 6. Object model (SOLID, for a later build)

| Type | Responsibility |
| --- | --- |
| `Schedule5NameSource` (Protocol) | Load names from `docs/schedule5.md` |
| `MarkdownBulletNameSource` | Parse `- ` lines |
| `VirusNameNormaliser` | Normalisation in §3 |
| `VirusNameInteractor` | True/false interaction, including synonym table |
| `Schedule5CsvAnnotator` | Rewrite Schedule 5; do not parse PDFs |
| `UnmatchedNameSink` | Write `output/schedule5_unmatched.txt` |

Do not fold this into `ApprovedVirusListParser`. The PDF parser does not own ATCSA Schedule 5 membership. The annotator depends on the CSV and the markdown list, not on pdfplumber.

## 7. Tests (when built)

Full Pytest contract: [build.schedule5.md](build.schedule5.md) §4. A request to run that build creates the modules and those tests.

Locks: 232 catalogue rows; 46 schedule-5 names; 7230 ICTV rows (inventory only). Names on `schedule5.md` partition into matched + unmatched. Virus names and all fields except Schedule 5 stay identical to the original `output/viruses.csv`.

## 8. Relation to spec.redteam.md

`spec.redteam.md` still owns PDF → CSV. It must not treat PDF `§` as the Schedule 5 value. This spec owns the terminal column after join. A later code change should replace empty/`§` cells with `1`/`0` using this document.
