# spec.cat1.md

**Status:** accepted (spec only; no implementation in this change)  
**Build:** [build.cat1.md](build.cat1.md)  
**Depends on:** [spec.redteam.md](spec.redteam.md) for `output/viruses.csv`  
**Gap list:** [../non-RNA_viruses.md](../non-RNA_viruses.md)  
**Sources:** `output/viruses.csv` (232 rows, 63 non-empty genera), `docs/ICTV_RNA_virus_species_MSL41.csv` (7230 rows)

## 1. Goal

The taxonomic join key between `output/viruses.csv` and `docs/ICTV_RNA_virus_species_MSL41.csv` is **`Genus`**.

`Genus` strings that name the same taxon are harmonized semantically to an ICTV `Genus` (`NEN genus`) before the join. The pool for each catalogue row is the ICTV rows in `NEN genus`.

For each catalogue row:

1. Set `NEN genus` to the ICTV `Genus` that is the same taxon as the catalogue `Genus` (§4).
2. Harmonize `Virus` to the ICTV `Exemplar virus` names inside that `NEN genus` (`NEN virus`, including serotypes, types, and genotypes).
3. Remove those matched `Exemplar virus` rows from that `NEN genus` (`EXCEPT`).
4. Collect Category 1 viruses from what remains in that `NEN genus`. The sample size of an ICTV genus is the number of catalogue rows whose `NEN genus` is that genus.

Genera in `output/viruses.csv` that belong to DNA or reverse-transcribing viruses are listed in [non-RNA_viruses.md](../non-RNA_viruses.md) and are absent from `ICTV_RNA_virus_species_MSL41.csv`. No Category 1 viruses are collected for those genera.

This change does not generate `output/nen_viruses.csv` or `output/ICTV_cat1.csv`.

## 2. Inputs and keys

### 2.1 `output/viruses.csv`

Catalogue from [spec.redteam.md](spec.redteam.md). Read and left unchanged (**232** data rows).

| Role | Column |
| --- | --- |
| Taxonomic join key, after harmonization | `NEN genus` (the ICTV `Genus`; §4) |
| Catalogue genus to harmonize | `Genus` |
| Virus-name key to harmonize | `Virus` |

`Family` is carried only for context; it is **not** the join key between the two tables (for example, `Orbivirus`, `Rotavirus`, `Orthoreovirus`, `Coltivirus`, and `Seadornavirus` are under `Reoviridae` in `viruses.csv` and under `Sedoreoviridae`/`Spinareoviridae` in ICTV, and `Pegivirus` is under `Flaviviridae` in `viruses.csv` and `Hepaciviridae` in ICTV — all match directly on `Genus`).

### 2.2 `docs/ICTV_RNA_virus_species_MSL41.csv`

Inventory of **7230** data rows and **21** columns. Read and left unchanged.

| Role | Column |
| --- | --- |
| Taxonomic join key | `Genus` (written into `NEN genus` when it is the chosen taxon) |
| Virus-name key | `Exemplar virus` |

## 3. Genus alignment

### 3.1 Genera found in ICTV (`42` genera, `690` ICTV rows)

42 distinct `Genus` values in `output/viruses.csv` match `Genus` in `docs/ICTV_RNA_virus_species_MSL41.csv` directly:

`Alphacoronavirus`, `Alphainfluenzavirus`, `Alphavirus`, `Bandavirus`, `Betacoronavirus`, `Betainfluenzavirus`, `Cardiovirus`, `Coltivirus`, `Cosavirus`, `Deltainfluenzavirus`, `Deltavirus`, `Enterovirus`, `Gammainfluenzavirus`, `Henipavirus`, `Hepatovirus`, `Lyssavirus`, `Mammarenavirus`, `Metapneumovirus`, `Morbillivirus`, `Norovirus`, `Orbivirus`, `Orthoavulavirus`, `Orthobornavirus`, `Orthobunyavirus`, `Orthoebolavirus`, `Orthoflavivirus`, `Orthohantavirus`, `Orthomarburgvirus`, `Orthopneumovirus`, `Orthoreovirus`, `Orthorubulavirus`, `Parechovirus`, `Paslahepevirus`, `Pegivirus`, `Phlebovirus`, `Respirovirus`, `Rotavirus`, `Rubivirus`, `Seadornavirus`, `Thogotovirus`, `Torovirus`, `Vesiculovirus`.

### 3.2 Genus strings that need semantic harmonization

§4 assigns each of these an `NEN genus`. The first two genus strings are not ICTV genera. The Sapporo row’s genus string is an ICTV genus, and the virus is in a different one. The Astroviridae row has no genus string.

| Catalogue `Genus` | Catalogue `Virus` | `NEN genus` |
| --- | --- | --- |
| `Ortonairovirus` | the five Nairoviridae rows | `Orthonairovirus` |
| `Hepacivirus` | `Hepatitis C virus, HCV, (also known as Hepacivirus C virus)` | `Orthohepacivirus` |
| `Norovirus` | `Sapporo virus (also known as Human calicivirus SLV)` | `Sapovirus` |
| blank | `Astroviridae spp. known to be pathogenic in humans` | `Mamastrovirus` |

An exact `Genus` match is copied into `NEN genus` with no model call. `Norwalk virus` stays `Norovirus`. `Pegivirus` stays `Pegivirus`. The five reovirus genera stay themselves.

### 3.3 Non-RNA genera absent from ICTV (`19` genera + `2` blank-genus DNA rows)

The DNA and reverse-transcribing genera (`Alphatorquevirus`, `Betapolyomavirus`, `Bocaparvovirus`, `Cytomegalovirus`, `Deltaretrovirus`, `Erythroparvovirus`, `Gammaretrovirus`, `Lentivirus`, `Lymphocryptovirus`, `Molluscipoxvirus`, `Orthohepadnavirus`, `Orthopoxvirus`, `Parapoxvirus`, `Rhadinovirus`, `Roseolavirus`, `Simplex virus`, `Tetraparvovirus`, `Varicellovirus`, `Yatapoxvirus`, plus the blank-genus `Adenoviridae` and `Papillomaviridae` rows) are absent from the ICTV RNA file and documented in [non-RNA_viruses.md](../non-RNA_viruses.md).

## 4. Semantic harmonization of `Genus` (`NEN genus`)

`NEN genus` is the ICTV `Genus` used as the join key for that catalogue row. It is written on `output/nen_viruses.csv`. It is either an exact `Genus` value from `docs/ICTV_RNA_virus_species_MSL41.csv` or empty. It is not a paraphrase.

### 4.1 Order

The virus prompt cannot run until `NEN genus` is set, and a virus that sits in a different genus from its catalogue `Genus` is only visible after the virus prompt fails. The order is:

1. If the catalogue `Genus` equals an ICTV `Genus`, set `NEN genus` to that string and run the virus prompt (§5.2). `Norwalk virus` stays in `Norovirus`.
2. If that virus prompt returns no exemplar, and the row is not a catch-all, run the genus prompt (§4.2) and run the virus prompt again in the genus it returns. Replace `NEN genus` only when that second virus prompt returns one or more exemplars. This is how `Sapporo virus` moves from catalogue `Norovirus` to `Sapovirus`. If the genus prompt returns none, or the second virus prompt returns none, `NEN genus` stays the copied catalogue genus and `Issues` is `unresolved name`.
3. If the catalogue `Genus` is not an ICTV `Genus`, or is blank, run the genus prompt first (§4.2), then the virus prompt in that `NEN genus`. This covers `Ortonairovirus`, `Hepacivirus`, and the blank Astroviridae row.

### 4.2 Genus prompt

The prompt receives `Family`, `Genus`, and `Virus` from the catalogue row, and a candidate list of ICTV `Genus` names. It returns one candidate, copied exactly, or none. A reply that is not a candidate is none. The prompt does not ask for sequences, culture, or hazard groups.

The candidate list is not the full set of ICTV genera. It is:

1. The ICTV genera whose `Family` equals the catalogue `Family`, when that family is an ICTV family. `Nairoviridae` supplies `Orthonairovirus`. `Caliciviridae` supplies `Sapovirus`. `Astroviridae` supplies `Mamastrovirus` and `Avastrovirus`.
2. ICTV genera whose name contains the catalogue genus stem, and only when the catalogue `Genus` is not already in the step-1 list. The stem is the casefolded catalogue genus, and it is used when its length is at least 6. The stem of `Hepacivirus` matches `Orthohepacivirus`, which sits in `Hepaciviridae`, not in catalogue `Flaviviridae`. A catalogue genus that is already in the step-1 list, such as `Norovirus` inside `Caliciviridae`, does not add stem matches. `Sapovirus` is already in that step-1 list.

DNA and reverse-transcribing genera have no candidate. `NEN genus` is empty and `Issues` is `genus not in ICTV`.

The blank Astroviridae catch-all names human pathogens and no genus. `NEN genus` is `Mamastrovirus`. Its `NEN virus` is the human exemplar `mamastrovirus 1`, not the other species in that genus.

## 5. Name harmonization inside `NEN genus` (`Viruses`, `NEN virus`)

Inside `NEN genus`, `Virus` and `Exemplar virus` are harmonized the same way (`Zaire ebolavirus` and `Ebola virus`, `St Louis encephalitis virus` and `St. Louis encephalitis virus`, a parenthetical alias, `Dengue virus` and `dengue virus type 2`).

### 5.1 `output/nen_viruses.csv`

Header:

```text
Family,Genus,NEN genus,Viruses,NEN virus,Issues
```

`Genus` is the catalogue genus. `NEN genus` is the ICTV genus from §4.

`Viruses` holds the catalogue `Virus` string. `NEN virus` holds one ICTV `Exemplar virus` string from `NEN genus`. When one catalogue virus covers multiple ICTV exemplars in `G` (serotypes, types, or genotypes), `Viruses` is repeated on one row per matched exemplar:

```text
Flaviviridae,Orthoflavivirus,Orthoflavivirus,Dengue virus,dengue virus type 1,
Flaviviridae,Orthoflavivirus,Orthoflavivirus,Dengue virus,dengue virus type 2,
Flaviviridae,Orthoflavivirus,Orthoflavivirus,Dengue virus,dengue virus type 3,
Flaviviridae,Orthoflavivirus,Orthoflavivirus,Dengue virus,dengue virus type 4,
```

(In `docs/ICTV_RNA_virus_species_MSL41.csv`, `Orthoflavivirus denguei` only has `dengue virus type 2` as its `Exemplar virus`; in `Deltavirus`, `Hepatitis D virus` expands to `hepatitis D virus 1` through `8`; in `Orthoflavivirus`, tick-borne encephalitis expands to `tick-borne encephalitis virus 1` and `2`.)

### 5.2 Virus prompt

For each catalogue row with a non-empty `NEN genus` `G`, the prompt receives:

- `NEN genus` `G` and `Virus`
- the candidate list: `Exemplar virus` values in ICTV genus `G`, and only those values

The prompt returns every candidate in `G` that is that virus, including listed serotypes, types, and genotypes, one candidate per line, copied exactly, or none. A line that is not a candidate is dropped. An `Exemplar virus` cell that contains `;` or `,` is one candidate, not several.

A catalogue row is a catch-all when its `Virus` text contains `spp.`, starts with `Other `, or contains `species not listed`. The `catchall` label is written only when that row also matches no exemplar. If the virus prompt returns exemplars, those rows are written with an empty `Issues` cell. `Novel coronaviridae spp.` is a catch-all. A row such as `Human rhinovirus A spp. known to be pathogenic in humans` is a catch-all only when the virus prompt returns nothing.

| Catalogue row | Rows written | `NEN virus` | `Issues` |
| --- | --- | --- | --- |
| One or more candidates in `NEN genus` match | one row per matched exemplar | that `Exemplar virus` | empty |
| `NEN genus` empty because the genus is not in the RNA table | one row | empty | `genus not in ICTV` |
| Open catch-all that names no exemplar | one row | empty | `catchall` |
| No candidate in `NEN genus` | one row | empty | `unresolved name` |

## 6. `EXCEPT` on `NEN genus`, then sample

For each ICTV genus `G` that appears as an `NEN genus`:

```text
pool(G)      = ICTV rows with Genus = G
remove(G)    = non-empty NEN virus values whose NEN genus is G
remainder(G) = pool(G) EXCEPT rows whose Exemplar virus is in remove(G)
```

The sample size `N(G)` is the number of catalogue rows whose `NEN genus` is the ICTV genus `G`, including a row whose `NEN virus` is empty. The sample is the first `N(G)` rows of `remainder(G)` in ICTV source order. A catalogue genus that splits across two ICTV genera, as `Norovirus` does when the Sapporo row moves to `Sapovirus`, contributes to each `N(G)` separately: `Sapovirus` has sample size 1, and `Norovirus` keeps the catalogue rows that stayed there.

Where `remainder(G)` has fewer rows than the sample size, the sample is what remains. Rows are not invented. `Alphainfluenzavirus`, `Betainfluenzavirus`, `Deltainfluenzavirus`, `Gammainfluenzavirus`, `Norovirus`, and `Orthomarburgvirus` each have one ICTV row. `Deltavirus` has none left after `hepatitis D virus 1` through `8` are removed.

## 7. Output (`output/ICTV_cat1.csv`)

Seven columns are retained from the ICTV row, in this order:

```text
Species, Exemplar virus, Family, Genus, Kingdom, GenBank accessions, RefSeq accessions
```

Three fields are then added, in this order:

```text
Human pathogen hazard group, Schedule 5, Issues
```

Header line:

```text
Species,Exemplar virus,Family,Genus,Kingdom,GenBank accessions,RefSeq accessions,Human pathogen hazard group,Schedule 5,Issues
```

On every data row:

| Field | Value |
| --- | --- |
| `Human pathogen hazard group` | `1` |
| `Schedule 5` | `0` |
| `Issues` | empty |

Harmonization notes (`genus not in ICTV`, `catchall`, `unresolved name`) are written on `output/nen_viruses.csv`. They are not copied onto `output/ICTV_cat1.csv`. A short remainder is visible because the sample has fewer than `N(G)` rows.

`output/viruses.csv` and `docs/ICTV_RNA_virus_species_MSL41.csv` are unchanged. Sampling reads `output/nen_viruses.csv` and does not call a prompt. The harmonizer runs when that file is absent, or when the operator asks to refresh it.

## 8. Object model (SOLID, for a later build)

| Type | Responsibility |
| --- | --- |
| `CatalogueGenusIndex` | Read the `output/viruses.csv` rows (`Family`, `Genus`, `Virus`) |
| `IctvGenusInventory` | Index ICTV rows by `Genus`, and list the ICTV genus names |
| `GenusCandidateList` | Build the §4.2 candidate genera for one catalogue row |
| `GenusNenPrompt` (Protocol) | Catalogue row plus those candidates → one ICTV genus or none |
| `VirusNenPrompt` (Protocol) | `NEN genus`, `Virus`, and the exemplars in that genus → the matching exemplars, including serotypes, or none |
| `NenHarmonizer` | Assign `NEN genus` and `NEN virus` for each catalogue row |
| `NenWriter` | Write `output/nen_viruses.csv` |
| `NenReader` | Read `output/nen_viruses.csv` back into rows for `EXCEPT` and sampling |
| `GenusVirusExcept` | Remove ICTV rows in `NEN genus` whose `Exemplar virus` is a non-empty `NEN virus` |
| `GenusCategory1Sampler` | Count `N(G)` by `NEN genus` and take the first `N(G)` rows of `remainder(G)` in ICTV source order |
| `IctvCat1Writer` | Write `output/ICTV_cat1.csv` (§7) |
| `BuildCategory1` | Run harmonize, or read an existing `nen_viruses.csv`, then sample |
