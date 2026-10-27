# non-RNA_viruses.md

**Status:** accepted  
**HSE source:** *The Approved List of biological agents* (`docs/misc208.pdf`, sixth edition, 2026), parsed to `output/viruses.csv`  
**ICTV source:** `docs/ICTV_RNA_virus_species_MSL41.csv` (7230 species)  
**Category 1 join:** [specs/spec.cat1.md](specs/spec.cat1.md)

## 1. What this list is

The taxonomic join between `output/viruses.csv` and `docs/ICTV_RNA_virus_species_MSL41.csv` is on **`Genus`**.

When joined on `Genus`:

- **42** genera in `output/viruses.csv` match `Genus` in `docs/ICTV_RNA_virus_species_MSL41.csv` directly (including all 5 `Reoviridae` genera: `Coltivirus`, `Orbivirus`, `Orthoreovirus`, `Rotavirus`, `Seadornavirus`, and `Pegivirus`).
- **9** virus families in `output/viruses.csv` (spanning **19** named genera and **2** blank-genus rows) are DNA or reverse-transcribing viruses and are absent from the ICTV RNA file. No Category 1 rows are collected for them.

## 2. DNA virus families and genera absent from ICTV RNA (`7` families)

| HSE `Family` | HSE `Genus` values in `output/viruses.csv` | Rows in `viruses.csv` |
| --- | --- | ---: |
| `Adenoviridae` | *(blank — family catch-all)* | 1 |
| `Anelloviridae` | `Alphatorquevirus` | 1 |
| `Orthoherpesviridae` | `Cytomegalovirus`, `Lymphocryptovirus`, `Rhadinovirus`, `Roseolavirus`, `Simplex virus`, `Varicellovirus` | 10 |
| `Papillomaviridae` | *(blank — family catch-all)* | 1 |
| `Parvoviridae` | `Bocaparvovirus`, `Erythroparvovirus`, `Tetraparvovirus` | 4 |
| `Polyomaviridae` | `Betapolyomavirus` | 5 |
| `Poxviridae` | `Molluscipoxvirus`, `Orthopoxvirus`, `Parapoxvirus`, `Yatapoxvirus` | 9 |

## 3. Reverse-transcribing families and genera absent from ICTV RNA (`2` families)

| HSE `Family` | HSE `Genus` values in `output/viruses.csv` | Genome | Rows in `viruses.csv` |
| --- | --- | --- | ---: |
| `Hepadnaviridae` | `Orthohepadnavirus` | DNA reverse-transcribing | 1 |
| `Retroviridae` | `Deltaretrovirus`, `Gammaretrovirus`, `Lentivirus` | RNA reverse-transcribing | 6 |

## 4. Note on `Reoviridae` when joining on `Genus`

In `output/viruses.csv`, `Coltivirus`, `Orbivirus`, `Orthoreovirus`, `Rotavirus`, and `Seadornavirus` are listed under `Family = Reoviridae`. In `docs/ICTV_RNA_virus_species_MSL41.csv`, ICTV split `Reoviridae` into `Sedoreoviridae` and `Spinareoviridae`, **but kept all five `Genus` names unchanged**:

| `Genus` | ICTV `Family` in MSL41 | ICTV species rows |
| --- | --- | ---: |
| `Orbivirus` | `Sedoreoviridae` | 22 |
| `Rotavirus` | `Sedoreoviridae` | 11 |
| `Seadornavirus` | `Sedoreoviridae` | 3 |
| `Orthoreovirus` | `Spinareoviridae` | 10 |
| `Coltivirus` | `Spinareoviridae` | 5 |

Because [spec.cat1.md](specs/spec.cat1.md) joins on **`Genus`**, all five genera are matched in ICTV and are not missing.
