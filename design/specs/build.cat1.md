# build.cat1.md

**Status:** accepted  
**Companion spec:** [spec.cat1.md](spec.cat1.md)  
**Target:** write `output/nen_viruses.csv` and `output/ICTV_cat1.csv`

## Execution rule

Reading or editing this file does **not** create Python.

A request to **run this build** (this document named, or “run `build.cat1.md`”) **does** create the modules and the Pytest files in §1 and §4, then runs:

```bash
python3 -m pytest tests/unit/category1 tests/integration/test_category1_workflow.py tests/integration/test_category1_end_to_end.py -q
```

Do not fold these types into `ApprovedVirusListParser`. Do not import pdfplumber. Do not call a model from tests. Do not write the repo copies of `output/viruses.csv` or `docs/ICTV_RNA_virus_species_MSL41.csv`.

## 0. Locked inventory

| File | What is counted | Count |
| --- | --- | --- |
| `docs/ICTV_RNA_virus_species_MSL41.csv` | data rows | **7230** |
| `output/viruses.csv` | data rows | **232** |
| catalogue genera that equal an ICTV `Genus` | distinct strings | **42** |

## 1. Modules created when this build is run

| Module | Type |
| --- | --- |
| `src/virus_redteaming/category1/models.py` | `CatalogueVirus`, `IctvSpecies`, `NenRow`, `Cat1Row` |
| `src/virus_redteaming/category1/protocols.py` | `GenusNenPrompt`, `VirusNenPrompt` |
| `src/virus_redteaming/category1/inventory.py` | `CatalogueGenusIndex`, `IctvGenusInventory` |
| `src/virus_redteaming/category1/candidates.py` | `GenusCandidateList` |
| `src/virus_redteaming/category1/harmonize.py` | `NenHarmonizer` |
| `src/virus_redteaming/category1/except_sample.py` | `GenusVirusExcept`, `GenusCategory1Sampler` |
| `src/virus_redteaming/category1/write.py` | `NenWriter`, `NenReader`, `IctvCat1Writer` |
| `src/virus_redteaming/category1/workflow.py` | `BuildCategory1`, `Category1PromptRequired` |
| `src/virus_redteaming/__main__.py` | subcommand `category1` only; no prompt text |
| `tests/unit/category1/test_genus_candidates.py` | §4.2 |
| `tests/unit/category1/test_nen_harmonizer.py` | §4.3 |
| `tests/unit/category1/test_except_sample.py` | §4.4 |
| `tests/unit/category1/test_writers.py` | §4.5 |
| `tests/integration/test_category1_workflow.py` | §4.6 |
| `tests/integration/test_category1_end_to_end.py` | §4.7 |

Paths used by tests live in `tests/conftest.py`. Package code receives paths through constructors and `run`.

## 2. Pseudocode

Each block is the whole behaviour of that type. A name written `like_this` is a value already defined above. Prompts are injected. They are not called with a model client in tests.

### 2.1 Values

Four frozen values. `catalogue_index` is the position of the source row in `viruses.csv`. It is how a later count tells one catalogue virus from the several `NenRow`s it may produce. It is not a CSV column.

```
CatalogueVirus
    catalogue_index : int
    family          : str
    genus           : str          # "" when the PDF cell was blank
    virus           : str

IctvSpecies
    source_index : int             # 0 for the first ICTV data row
    species      : str
    exemplar     : str             # the Exemplar virus cell, unsplit
    family       : str
    genus        : str
    kingdom      : str
    genbank      : str             # copied as stored, including "" and "L: …; M: …; S: …"
    refseq       : str

NenRow
    catalogue_index : int
    family          : str          # catalogue family
    genus           : str          # catalogue genus
    nen_genus       : str          # an ICTV genus, or ""
    viruses         : str          # the catalogue virus, repeated on each serotype row
    nen_virus       : str          # one ICTV exemplar, or ""
    issues          : str          # "", "genus not in ICTV", "catchall", or "unresolved name"

Cat1Row
    species, exemplar, family, genus, kingdom, genbank, refseq : str
    hazard_group : str = "1"
    schedule_5   : str = "0"
    issues       : str = ""
```

### 2.2 Read the two tables

`CatalogueGenusIndex` reads `Family`, `Genus`, and `Virus` only. It does not count rows and it does not look at hazard group or Schedule 5.

```
read(path) -> tuple[CatalogueVirus, ...]:
    rows ← []
    for i, record in enumerate(csv.DictReader(path)):
        rows.append(CatalogueVirus(
            catalogue_index = i,
            family = record["Family"],
            genus  = record["Genus"],
            virus  = record["Virus"],
        ))
    return tuple(rows)
```

`IctvGenusInventory` is constructed from rows already in memory. `from_csv` is the file loader. Unit tests pass a list and do not open the repo CSV.

```
__init__(rows: tuple[IctvSpecies, ...]):
    self.rows ← rows

from_csv(path) -> IctvGenusInventory:
    rows ← []
    for i, record in enumerate(csv.DictReader(path)):
        rows.append(IctvSpecies(
            source_index = i,
            species  = record["Species"],
            exemplar = record["Exemplar virus"],    # one cell, even when it contains ";" or ","
            family   = record["Family"],
            genus    = record["Genus"],
            kingdom  = record["Kingdom"],
            genbank  = record["GenBank accessions"],
            refseq   = record["RefSeq accessions"],
        ))
    return IctvGenusInventory(tuple(rows))

genera() -> tuple[str, ...]:
    # distinct Genus values, first-seen order, skip ""
    return unique(row.genus for row in self.rows if row.genus != "")

by_genus(genus) -> tuple[IctvSpecies, ...]:
    return every self.rows entry whose genus equals genus, still in source order

exemplars(genus) -> tuple[str, ...]:
    # the Exemplar virus cells of by_genus(genus), in that same order
    # do not split a cell on ";" or ","
    return unique(row.exemplar for row in by_genus(genus))

families() -> frozenset[str]:
    return {row.family for row in self.rows}
```

### 2.3 Which ICTV genera the genus prompt may choose

`GenusCandidateList.candidates(row)` builds the list the genus prompt is allowed to return. It is not the 1442 ICTV genera.

```
candidates(row, inventory) -> tuple[str, ...]:
    # Step 1. Genera in the same ICTV family, when the catalogue family exists there.
    if row.family is in inventory.families():
        in_family ← unique genus of inventory rows whose family equals row.family
                     in ICTV source order
    else:
        in_family ← ()

    # Step 2 only when the catalogue genus is not already in the step-1 list.
    # Norovirus is already a Caliciviridae genus, so Sapovirus comes from step 1
    # and no stem search is run. Hepacivirus is not a Flaviviridae genus, so the
    # stem "hepacivirus" adds Orthohepacivirus from Hepaciviridae.
    if row.genus is in in_family or length(casefold(row.genus)) < 6:
        by_stem ← ()
    else:
        stem ← casefold(row.genus)
        by_stem ← ICTV genera G where casefold(G) contains stem and G is not in in_family
                   in ICTV source order

    return in_family followed by by_stem
```

A blank genus is not in `in_family` and its stem length is 0, so step 2 adds nothing. `Astroviridae` then offers `Mamastrovirus` and `Avastrovirus` from step 1. A DNA family that is not an ICTV family gets an empty list from both steps.

### 2.4 What a prompt reply is allowed to be

The harmonizer checks the reply. A prompt that returns something outside the list it was given is treated as no answer.

```
accept_genus(reply, candidates) -> str:
    if reply is one of candidates:
        return reply
    return ""

accept_exemplars(reply_lines, exemplars) -> tuple[str, ...]:
    kept ← []
    for line in reply_lines:                 # already split on newlines, never on "," or ";"
        if line is one of exemplars and line is not already in kept:
            kept.append(line)
    return tuple(kept)
```

```
GenusNenPrompt.choose(row, candidates) -> str | None
VirusNenPrompt.choose(nen_genus, virus, exemplars) -> tuple[str, ...]
```

`nen_genus` is the genus whose exemplar list was offered. `choose` returns every exemplar in that genus that is the same virus, including listed serotypes, types, and genotypes, one exact candidate per line.

### 2.5 Assign `NEN genus` and `NEN virus`

`NenHarmonizer` is the only type that calls the two prompts. Constructor: `candidates`, `genus_prompt`, `virus_prompt`. The ICTV inventory is an argument of `harmonize`, so the harmonizer and the sampler use the inventory loaded for that run.

A catch-all names a group and no single exemplar. It does not move to another genus when the first virus prompt misses.

```
is_catchall(virus) -> bool:
    text ← casefold(virus)
    return "spp." is in text
        or text starts with "other "
        or "species not listed" is in text
```

`Novel coronaviridae spp.` matches because of `spp.`. `Other Lyssavirus species not listed` matches because it starts with `other`. The label `catchall` is applied later, and only when the virus prompt returned nothing. A catch-all that does match exemplars is written as those exemplars with an empty `Issues` cell.

For one catalogue row the harmonizer follows exactly one of three paths.

```
harmonize_one(row, inventory) -> tuple[NenRow, ...]:
    genus_is_ictv ← row.genus != "" and row.genus is in inventory.genera()

    # Path A. The catalogue genus is already an ICTV genus.
    # Copy it. Ask which exemplars in that genus are this virus.
    # Norwalk virus stays in Norovirus here.
    if genus_is_ictv:
        nen_genus ← row.genus
        matches ← ask_virus(row.virus, nen_genus, inventory)

        # Path A2. The virus was not in that genus, and this row is not a catch-all.
        # Ask for a different genus, then ask the virus prompt again.
        # Move only when that second answer names at least one exemplar.
        # Sapporo virus: Norovirus misses, Sapovirus hits, so NEN genus becomes Sapovirus.
        # If the genus prompt returns none, or the second virus prompt returns none,
        # NEN genus stays the copied catalogue genus. Issues becomes unresolved name.
        if matches is empty and not is_catchall(row.virus):
            alt ← ask_genus(row, inventory)
            alt_matches ← ask_virus(row.virus, alt, inventory)
            if alt != "" and alt_matches is not empty:
                nen_genus ← alt
                matches ← alt_matches

    # Path B. The catalogue genus is missing, misspelled, or blank.
    # Ask for a genus first, then ask the virus prompt in that genus.
    # Ortonairovirus, Hepacivirus, and the blank Astroviridae row take this path.
    else:
        nen_genus ← ask_genus(row, inventory)
        matches ← ask_virus(row.virus, nen_genus, inventory)

    return emit(row, nen_genus, matches)

ask_genus(row, inventory) -> str:
    offered ← candidates.candidates(row, inventory)
    reply ← genus_prompt.choose(row, offered)
    return accept_genus(reply, offered)

ask_virus(virus, nen_genus, inventory) -> tuple[str, ...]:
    if nen_genus == "":
        return ()                          # do not call the virus prompt
    offered ← inventory.exemplars(nen_genus)
    reply ← virus_prompt.choose(nen_genus, virus, offered)
    return accept_exemplars(reply, offered)
```

`emit` turns that answer into CSV rows. One catalogue virus that matches several exemplars becomes several rows. `Viruses` is the same catalogue string on each of them.

```
emit(row, nen_genus, matches) -> tuple[NenRow, ...]:
    if matches is not empty:
        return one NenRow per exemplar in matches, with
            nen_genus = nen_genus
            viruses   = row.virus
            nen_virus = that exemplar
            issues    = ""

    # No exemplar. One row, nen_virus empty, one issue label.
    if nen_genus == "":
        label ← "genus not in ICTV"
    else if is_catchall(row.virus):
        label ← "catchall"
    else:
        label ← "unresolved name"

    return one NenRow with nen_virus = "" and issues = label
```

```
harmonize(catalogue, inventory) -> tuple[NenRow, ...]:
    rows ← []
    for row in catalogue:
        rows.extend(harmonize_one(row, inventory))
    return tuple(rows)
```

Worked assignments:

| Catalogue row | Path | `NEN genus` | `NEN virus` |
| --- | --- | --- | --- |
| `Norovirus` / `Norwalk virus` | A, virus prompt hits | `Norovirus` | `Norwalk virus` |
| `Norovirus` / `Sapporo virus …` | A, virus prompt misses, then A2 | `Sapovirus` | `Sapporo virus` |
| `Ortonairovirus` / a nairovirus | B | `Orthonairovirus` | the exemplar the virus prompt returns |
| `Hepacivirus` / hepatitis C | B | `Orthohepacivirus` | `hepatitis C virus genotype 1a` |
| blank / `Astroviridae spp. …` | B | `Mamastrovirus` | `mamastrovirus 1` |
| `Orthopoxvirus` / any virus | B, no candidates | empty | empty, issues `genus not in ICTV` |

### 2.6 Remove the matched exemplars, then take the first `N(G)`

`GenusVirusExcept` does not call a prompt. For each ICTV genus `G` that some `NenRow` uses:

```
pool(G)      = inventory.by_genus(G)                         # ICTV source order
offered(G)   = inventory.exemplars(G)
remove(G)    = {row.nen_virus for NenRow row
                where row.nen_genus == G
                  and row.nen_virus is in offered(G)}
remainder(G) = the pool rows whose exemplar is not in remove(G)
               still in ICTV source order
```

Membership is exact string equality. A `NEN virus` that is not one of the exemplar cells in `G` removes nothing. An exemplar is removed only inside its own `NEN genus`. The same spelling in another genus stays.

`GenusCategory1Sampler` then cuts each remainder down to the number of catalogue rows that landed in that genus.

```
sample(nen_rows, remainder) -> tuple[IctvSpecies, ...]:
    genus_order ← nen_genus values in the order they first appear in nen_rows, skipping ""
    chosen ← []
    for G in genus_order:
        N ← how many distinct catalogue_index values have nen_genus == G
        # a row with an empty nen_virus still counts
        # eight hepatitis D NenRows from one catalogue_index count as N = 1
        chosen.extend(remainder(G)[0 : N])      # fewer than N when the remainder is shorter
    return tuple(chosen)
```

No row is invented to fill a short remainder. `Alphainfluenzavirus` has one ICTV row, so its sample length is at most 1. After `hepatitis D virus 1` through `8` are in `remove(Deltavirus)`, that remainder is empty and the sample for `Deltavirus` is empty.

A catalogue genus that splits is two sample sizes. When Sapporo moves to `Sapovirus` and Norwalk stays in `Norovirus`, `N(Sapovirus)` and `N(Norovirus)` are counted separately.

Trace, one genus, four ICTV rows in source order, `N = 2`, and the second exemplar listed as a `NEN virus`:

```
pool       A  B  C  D
remove        B
remainder  A     C  D
sample     A     C          # the first 2 of the remainder, not rows 0 and 1 of the pool
```

### 2.7 Write the two CSV files

```
NenWriter.write(path, nen_rows):
    header = Family,Genus,NEN genus,Viruses,NEN virus,Issues
    for row in nen_rows:
        write row.family, row.genus, row.nen_genus, row.viruses, row.nen_virus, row.issues
        # catalogue_index is not a column

NenReader.read(path) -> tuple[NenRow, ...]:
    # Serotype repeats are written one after another. The file has no catalogue_index.
    # The index increments when Family, Genus, or Viruses differs from the previous row.
    # A later catalogue row with the same three fields, after a different row, gets its own index.
    previous ← None
    next_index ← -1
    rows ← []
    for record in csv.DictReader(path):
        key ← (record["Family"], record["Genus"], record["Viruses"])
        if key != previous:
            next_index ← next_index + 1
            previous ← key
        rows.append(NenRow(
            catalogue_index = next_index,
            family = record["Family"],
            genus = record["Genus"],
            nen_genus = record["NEN genus"],
            viruses = record["Viruses"],
            nen_virus = record["NEN virus"],
            issues = record["Issues"],
        ))
    return tuple(rows)

IctvCat1Writer.write(path, species_rows):
    header = Species,Exemplar virus,Family,Genus,Kingdom,GenBank accessions,RefSeq accessions,Human pathogen hazard group,Schedule 5,Issues
    for species in species_rows:
        row ← Cat1Row from species, with hazard_group "1", schedule_5 "0", issues ""
        write row.species, row.exemplar, row.family, row.genus,
              row.kingdom, row.genbank, row.refseq,
              row.hazard_group, row.schedule_5, row.issues
```

`genbank` and `refseq` are the ICTV cells, including a blank cell and a segmented cell. They are not fetched and not split. `Issues` on a Category 1 row is always empty. Harmonization notes stay on `nen_viruses.csv`.

### 2.8 Run

```
BuildCategory1(
    catalogue_index: CatalogueGenusIndex,
    harmonizer: NenHarmonizer | None,
    exceptor: GenusVirusExcept,
    sampler: GenusCategory1Sampler,
    nen_writer: NenWriter,
    nen_reader: NenReader,
    cat1_writer: IctvCat1Writer,
)
```

`harmonizer` is `None` when no prompts are configured. Sampling never calls a prompt. The workflow does not construct a model client and does not contain prompt text.

```
run(viruses_path, ictv_path, nen_path, cat1_path, refresh) -> None:
    inventory ← IctvGenusInventory.from_csv(ictv_path)          # read
    if refresh or nen_path does not exist:
        if harmonizer is None:
            raise Category1PromptRequired
                # names nen_path; does not call a prompt
        catalogue_rows ← catalogue_index.read(viruses_path)    # read
        nen_rows ← harmonizer.harmonize(catalogue_rows, inventory)
        nen_writer.write(nen_path, nen_rows)
    else:
        nen_rows ← nen_reader.read(nen_path)                   # no prompt calls
    remainder ← exceptor.remainder(inventory, nen_rows)
    sample ← sampler.sample(nen_rows, remainder)
    cat1_writer.write(cat1_path, sample)
```

`viruses_path` and `ictv_path` are not opened for writing. CLI defaults, wired in `__main__.py` only. The CLI passes `harmonizer=None`.

```
category1
    --viruses  output/viruses.csv
    --ictv     docs/ICTV_RNA_virus_species_MSL41.csv
    --nen      output/nen_viruses.csv
    --out      output/ICTV_cat1.csv
    --refresh
```

Without `--refresh`, an existing `--nen` file is the input to `EXCEPT` and the sampler. `--refresh`, or a missing `--nen` file, raises `Category1PromptRequired` from the CLI because the CLI has no prompt implementation. Tests construct `NenHarmonizer` with the fakes in §4.1 and pass that harmonizer to `BuildCategory1`.

## 3. Invariants the tests lock

1. ICTV data rows stay 7230. Catalogue data rows stay 232. Neither file’s bytes change in a test.
2. A catalogue `Genus` that equals an ICTV `Genus` is copied to `NEN genus` before any genus prompt. It is replaced only when a later genus prompt returns a different genus and the virus prompt in that genus returns an exemplar. Otherwise the copied genus stays, including when the virus prompt returns nothing.
3. `Ortonairovirus` → `Orthonairovirus`. `Hepacivirus` → `Orthohepacivirus`. Sapporo’s `NEN genus` is `Sapovirus` and Norwalk’s stays `Norovirus`. Blank Astroviridae → `Mamastrovirus` and `NEN virus` `mamastrovirus 1`.
4. `GenusCandidateList` for `Hepacivirus` includes `Orthohepacivirus` and does not include every ICTV genus. `Adenoviridae` yields no genus.
5. A returned genus or exemplar that is not in the candidate list is dropped.
6. `EXCEPT` removes only exemplars present as non-empty `NEN virus` in that `NEN genus`.
7. The sample for genus `G` is the first `min(N(G), len(remainder))` rows of that remainder in ICTV source order. `N(G)` counts distinct catalogue rows.
8. Every `ICTV_cat1.csv` data row is a `Cat1Row`: hazard group `1`, Schedule 5 `0`, and an empty `Issues` cell. Its genus is an ICTV genus. No non-RNA catalogue genus appears. Harmonization notes stay on `nen_viruses.csv`.
9. For this ICTV file, dengue produces one `NEN virus`, `dengue virus type 2`, and that exemplar is absent from the Orthoflavivirus sample.
10. A `NEN virus` that is not an exemplar cell of its `NEN genus` removes no ICTV row. `Orthoebolavirus` contributes only `Bombali virus`. `tick-borne encephalitis virus 1` and `2` are absent from the sample. `Alphainfluenzavirus`, `Betainfluenzavirus`, `Deltainfluenzavirus`, `Gammainfluenzavirus`, `Norovirus`, `Orthomarburgvirus`, and `Deltavirus` contribute no Category 1 rows.

## 4. Pytest written when this build is run

### 4.1 Fakes

```
class FakeGenusPrompt:
    def choose(row, candidates) -> str | None:
        return the scripted genus if it is in candidates else None

class FakeVirusPrompt:
    def choose(nen_genus, virus, exemplars) -> tuple[str, ...]:
        return the scripted exemplars that are in exemplars
```

Unit tests build inventories from lists, not from the repo CSVs.

### 4.2 `tests/unit/category1/test_genus_candidates.py`

| Test | Asserts |
| --- | --- |
| `test_family_scope_for_nairoviridae` | Candidates for family `Nairoviridae` are the ICTV genera of that family, including `Orthonairovirus`. |
| `test_hepacivirus_stem_adds_orthohepacivirus` | Family `Flaviviridae` does not contain `Orthohepacivirus`. The stem adds it. |
| `test_genus_already_in_family_skips_the_stem` | Catalogue genus `Norovirus` is already in the `Caliciviridae` list. Candidates are that family list, including `Sapovirus`. Genera outside the family are not added. |
| `test_dna_family_has_no_candidates` | Family `Adenoviridae` and genus `Mastadenovirus` yield `()`. |
| `test_candidate_list_is_not_the_full_genus_inventory` | A two-family inventory does not return genera from the other family unless the stem matches. |

### 4.3 `tests/unit/category1/test_nen_harmonizer.py`

| Test | Asserts |
| --- | --- |
| `test_exact_genus_does_not_call_genus_prompt` | Genus `Norovirus`, virus prompt returns `Norwalk virus`. The virus prompt is called with `nen_genus` `Norovirus`. Genus prompt is not called. `NEN genus` is `Norovirus`. |
| `test_sapporo_retries_genus_after_virus_miss` | First virus call on `Norovirus` returns `()`. Genus prompt returns `Sapovirus`. Second virus call returns `Sapporo virus`. |
| `test_ortonairovirus_prompts_genus_first` | Genus is not in the inventory. Genus prompt is called before the virus prompt and returns `Orthonairovirus`. |
| `test_blank_astroviridae_resolves_mamastrovirus` | Genus prompt returns `Mamastrovirus`. Virus prompt returns `mamastrovirus 1`. One `NenRow`, issues empty. |
| `test_non_rna_genus_is_empty` | Genus prompt returns `None`. One row, `NEN genus` empty, issues `genus not in ICTV`. No virus-prompt call. |
| `test_off_list_genus_is_dropped` | Genus prompt returns `NotAGenus`. Treated as none. |
| `test_exact_genus_kept_when_retry_finds_nothing` | Genus is an ICTV genus. Virus prompt returns `()` in that genus and in the genus the retry offers. `NEN genus` stays the catalogue genus. `NEN virus` is empty. `Issues` is `unresolved name`. |
| `test_catchall_spp_does_not_move_genus` | Virus text is `Novel coronaviridae spp. (eg bat coronaviruses WIV1 or SHC01)`. Virus prompt returns `()`. Genus prompt is not called. `Issues` is `catchall`. |
| `test_serotype_rows_repeat_the_catalogue_virus` | Virus prompt returns two exemplars. Two `NenRow`s, same `Viruses`, different `NEN virus`. |
| `test_semicolon_exemplar_is_one_candidate` | The offered exemplar is `enterovirus E1; bovine enterovirus 1`. The virus prompt returns that whole string. One `NenRow`. The `;` is still inside `NEN virus`. |

### 4.4 `tests/unit/category1/test_except_sample.py`

| Test | Asserts |
| --- | --- |
| `test_except_removes_only_named_exemplars` | Remainder drops the `NEN virus` exemplar and keeps the next species in that genus. |
| `test_unknown_nen_virus_removes_nothing` | `NEN virus` is not an exemplar cell of that genus. The remainder is the whole pool. |
| `test_semicolon_exemplar_is_removed_whole` | `NEN virus` is `enterovirus E1; bovine enterovirus 1`. That one ICTV row is removed. A later row in the genus stays. The exemplar is not split on `;`. |
| `test_sample_is_the_first_n_in_source_order` | Remainder has 4 rows, `N` is 2. The sample is source index 0 and 1 of the remainder. |
| `test_short_remainder_is_not_padded` | `N` is 5, remainder has 1. The sample has length 1. |
| `test_split_genus_counts_each_nen_genus` | Two catalogue rows share catalogue genus `Norovirus`. One `NEN genus` is `Sapovirus`, one stays `Norovirus`. Each sample size is 1. |
| `test_expanded_serotypes_count_as_one_catalogue_row` | Three `NenRow`s that share one `catalogue_index` and `NEN genus` `Deltavirus` give `N` 1. |

### 4.5 `tests/unit/category1/test_writers.py`

| Test | Asserts |
| --- | --- |
| `test_nen_header` | Header is `Family,Genus,NEN genus,Viruses,NEN virus,Issues`. |
| `test_nen_reader_shares_one_index_across_serotypes` | Three contiguous rows with the same `Family`, `Genus`, and `Viruses` come back with one `catalogue_index`. |
| `test_nen_reader_restarts_index_after_a_different_row` | The same three fields appear, then a different virus, then the same three fields again. The two groups have different `catalogue_index` values. |
| `test_cat1_header_and_constants` | Header matches §2.7. The writer builds a `Cat1Row`. Hazard group is `1`, Schedule 5 is `0`, Issues is empty. GenBank text is unchanged, including a blank and a segmented cell. |

### 4.6 `tests/integration/test_category1_workflow.py`

Tiny catalogue CSV and tiny ICTV CSV under `tmp_path`. `BuildCategory1.run` with the fakes from §4.1.

| Test | Asserts |
| --- | --- |
| `test_workflow_writes_both_outputs` | `nen_viruses.csv` and `ICTV_cat1.csv` exist. A genus that was removed by `NEN virus` is absent from the sample. A later species in that genus is present when `N` allows it. |
| `test_workflow_does_not_rewrite_sources` | Byte size and first data row of the two input files are unchanged. |
| `test_existing_nen_skips_prompts` | A `nen_viruses.csv` is already under `tmp_path`. `run(..., refresh=False)` reads it and writes `ICTV_cat1.csv`. Neither prompt is called. |
| `test_missing_nen_without_harmonizer_raises` | `harmonizer` is `None` and `--nen` is absent. `run` raises `Category1PromptRequired`. No output file is written. |

### 4.7 `tests/integration/test_category1_end_to_end.py`

Reads the repo `output/viruses.csv` and `docs/ICTV_RNA_virus_species_MSL41.csv`. Writes both outputs under `tmp_path`. The prompts are fakes, not a model:

```
genus fake choose(row, candidates):
    catalogue genus Ortonairovirus → Orthonairovirus, if that candidate is offered
    catalogue genus Hepacivirus → Orthohepacivirus, if that candidate is offered
    blank genus and family Astroviridae → Mamastrovirus, if offered
    virus text contains "Sapporo virus" → Sapovirus, if offered
    anything else → None

virus fake choose(nen_genus, virus, exemplars):
    strip(text):
        repeatedly delete an innermost parenthetical, a "(...)" span with no parenthesis inside it
        if an unmatched "(" remains, delete from that "(" to the end
        delete one trailing ")"
        delete from " also known as" or " formerly" to the end
        casefold and collapse whitespace
    probes(virus):
        stripped ← strip(virus)
        probes ← [stripped]
        if stripped contains ",": add the text before the first comma
        add each probe with "haemorrhagic" and "hemorrhagic" exchanged
    if virus contains "Astroviridae spp.":
        return ("mamastrovirus 1",) when that exemplar is offered, else ()
    if nen_genus is "Alphainfluenzavirus" and "influenza A virus" is offered:
        return ("influenza A virus",)
    locked pairs, used only when the catalogue text contains the left-hand string:
        "Zaire ebolavirus" → "Ebola virus"
        "Bundibugyo ebolavirus" → "Bundibugyo virus"
        "Reston ebolavirus" → "Reston virus"
        "Sudan ebolavirus" → "Sudan virus"
        "Tai Forest ebolavirus" → "Taï Forest virus"
        "St Louis encephalitis virus" → "St. Louis encephalitis virus"
        "Far Eastern tick-borne encephalitis virus" → "tick-borne encephalitis virus 1"
        "Central European tick-borne encephalitis virus" → "tick-borne encephalitis virus 2"
    walk the offered exemplars in order and keep one when its casefold text equals a probe,
        or starts with a probe followed by a space,
        or it is the right-hand side of a locked pair
    return those exemplars in the order they were offered
```

This double is how the end-to-end test stays deterministic. It is not the production prompt. The spelling exchange covers `Crimean-Congo haemorrhagic fever virus` → `Crimean-Congo hemorrhagic fever virus`. `Hepatitis E virus)` loses the trailing `)`. An unclosed "(" , as on `Tai Forest ebolavirus (formerly …`, is cut off before the locked pair is applied.

`Norwalk virus (also known as human Calicivirus NLV)` probes as `norwalk virus`, so the first virus prompt hits and `NEN genus` stays `Norovirus`. `Sapporo virus (also known as Human calicivirus SLV)` misses in `Norovirus`, then matches `Sapporo virus` after the genus move. `Hepatitis C virus, HCV, (also known as Hepacivirus C virus)` probes as `hepatitis c virus`, which is a prefix of `hepatitis c virus genotype 1a`. `Hepatitis D virus also known as Delta virus` probes as `hepatitis d virus`, which is a prefix of `hepatitis d virus 1` through `8`.

| Test | Asserts |
| --- | --- |
| `test_sources_stay_at_locked_counts` | ICTV data rows are 7230. Catalogue data rows are 232. Both files are unread for writing. |
| `test_locked_nen_genus_rows` | The five `Ortonairovirus` rows have `NEN genus` `Orthonairovirus`. The Hepatitis C row has `Orthohepacivirus`. Sapporo has `Sapovirus`. Norwalk has `Norovirus`. The blank Astroviridae row has `Mamastrovirus` and `NEN virus` `mamastrovirus 1`. |
| `test_dengue_is_only_type_2` | The Dengue catalogue virus has one `NEN virus`, `dengue virus type 2`. That exemplar is not in `ICTV_cat1.csv`. |
| `test_cat1_rows_are_category_1_constants` | Every data row has hazard group `1`, Schedule 5 `0`, empty `Issues`, and a genus that occurs in the ICTV file. |
| `test_non_rna_genera_are_absent_from_the_sample` | No sample genus is one of the §3.3 genera, including `Orthopoxvirus`, `Lentivirus`, `Simplex virus`, and `Alphatorquevirus`. Those catalogue rows have empty `NEN genus` and issues `genus not in ICTV`. |
| `test_orthobunyavirus_sample_is_the_source_prefix` | Let `N` be the number of catalogue rows with `NEN genus` `Orthobunyavirus`, and `remainder` the ICTV Orthobunyavirus rows after the EXCEPT. The sample rows for that genus are `remainder[:N]` in source order. |
| `test_orthoebolavirus_sample_is_bombali_only` | The five catalogue ebolavirus rows map to `Ebola virus`, `Sudan virus`, `Bundibugyo virus`, `Reston virus`, and `Taï Forest virus`. The only `Orthoebolavirus` exemplar in `ICTV_cat1.csv` is `Bombali virus`. |
| `test_tick_borne_encephalitis_exemplars_are_removed` | Far Eastern maps to `tick-borne encephalitis virus 1`. Central European maps to `tick-borne encephalitis virus 2`. Neither exemplar is in `ICTV_cat1.csv`. |
| `test_short_genera_contribute_no_category_1_rows` | `Alphainfluenzavirus`, `Betainfluenzavirus`, `Deltainfluenzavirus`, `Gammainfluenzavirus`, `Norovirus`, `Orthomarburgvirus`, and `Deltavirus` do not appear in `ICTV_cat1.csv`. The six `Alphainfluenzavirus` rows have `NEN virus` `influenza A virus`. The Hepatitis D row has `NEN virus` `hepatitis D virus 1` through `8`. |
