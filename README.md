# virus_redteaming

Python research project for AI and LLM red-teaming of virus genome prompts. One workflow builds an HSE catalogue, joins it to ICTV, downloads NCBI FASTA, and records Claude replies. A second workflow searches NCBI from a virus-name list and downloads those sequences separately.

Organization: [ZikaLab](https://github.com/ZikaLab)  
Repository: [virus_redteaming](https://github.com/ZikaLab/virus_redteaming)

The package is typed object-oriented Python 3.11+. Agents follow `constitution/CONSTITUTION.md`. Specs and decisions are in `design/`.

## Layout

```
src/virus_redteaming/   importable package
tests/unit/             fast, isolated tests
tests/integration/      cross-module and IO tests
design/                 specs, ADRs, and architecture
constitution/           engineering constitution
docs/                   local source lists (not published)
output/                 generated tables and FASTA
scripts/                operator scripts (no business logic)
```

`docs/` and everything under `output/` except `output/.gitkeep` stay on the machine that runs the workflow. A clone does not contain the Approved List PDF, the ICTV table, the VMR, or generated CSV files.

## Requirements

- Python 3.11+
- `NCBI_EMAIL` with no spaces, for any command that calls NCBI. `NCBI_API_KEY` is optional.
- `ANTHROPIC_API_KEY` for `claude-red-team`. Optional `ANTHROPIC_MODEL` (default `claude-haiku-5-5`) and `ANTHROPIC_WORKSPACE_ID`. Copy `.env.example` to `.env`.

Place these files before the main workflow:

| Path | Role |
| --- | --- |
| `docs/misc208.pdf` | HSE/ACDP *Approved List of biological agents*, sixth edition |
| `docs/schedule5.md` | Schedule 5 virus names, one markdown bullet each |
| `docs/ICTV_RNA_virus_species_MSL41.csv` | ICTV RNA species table used by Category 1 |
| `docs/VMR_MSL41.v1.20260729.csv` | ICTV Virus Metadata Resource. Accessions are read from `Virus name(s)` and `Virus GENBANK accession` |
| `output/nen_viruses.csv` | Harmonized HSE rows. The CLI does not create this file |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,harness]"
pytest
```

The base install covers catalogue parsing and NCBI downloads. The `harness` extra installs the Claude client and `python-dotenv`. Run every command below from the repository root.

Live network tests stay off unless you opt in: `NCBI_LIVE_TEST=1` or `CLAUDE_LIVE_TEST=1`.

## Main workflow

Run the commands in this order. Each one reads the previous file and writes the next. `python -m virus_redteaming <command> --help` prints the flags.

### 1. Parse the Approved List

```bash
python -m virus_redteaming parse-viruses
```

Reads the **Viruses** tables on printed pages 27–42 of `docs/misc208.pdf` and writes `output/viruses.csv`. Pages before 27 and from 43 onward, including Annex 1, are not parsed. The hazard-group cell is copied as printed, so `3*` stays `3*`. The asterisk is a containment footnote, not Schedule 5.

`--pdf` and `--out` override the two paths. The command prints the number of rows written. The locked catalogue count is 232 data rows.

### 2. Mark Schedule 5

```bash
python -m virus_redteaming annotate-schedule-5
```

Reads virus names from the `- ` bullets in `docs/schedule5.md` and rewrites `output/viruses.csv` in place. Family, genus, virus name, hazard group, and row order stay the same. `Schedule 5` becomes `1` or `0`. One Schedule 5 name can mark more than one catalogue row. Names that match nothing are written to `output/schedule5_unmatched.txt`.

`--list` and `--csv` override the markdown list and the catalogue.

### 3. Sample Category 1

```bash
python -m virus_redteaming category1
```

This command requires `output/nen_viruses.csv` already on disk. It reads that file, removes the harmonized exemplars from each ICTV genus, and writes one Category 1 sample per catalogue row in that genus to `output/ICTV_cat1.csv`. Genera that are absent from the ICTV RNA species list contribute no Category 1 rows.

If `output/nen_viruses.csv` is missing, or if you pass `--refresh`, the command stops with `prompts required to write output/nen_viruses.csv`. This CLI does not call a model to harmonize names.

Other flags: `--viruses` (default `output/viruses.csv`), `--ictv` (default `docs/ICTV_RNA_virus_species_MSL41.csv`), `--nen`, `--out`.

### 4. Copy VMR accessions onto the HSE rows

```bash
python -m virus_redteaming assign-nen-accessions
```

Matches each `NEN virus` in `output/nen_viruses.csv` to the whole `Virus name(s)` cell in `docs/VMR_MSL41.v1.20260729.csv`. Matching strips a non-breaking space and surrounding whitespace and keeps case. When several VMR rows share that name, the exemplar (`E`) is used. A name with no exemplar keeps the first row. The chosen `Virus GENBANK accession` is parsed into the `NCBI accession` column and the nen file is rewritten.

The command prints the matched count, each unmatched `NEN virus`, and the number of blank `NEN virus` cells. `--nen` and `--vmr` override the two paths.

### 5. Merge HSE and Category 1

```bash
python -m virus_redteaming merge-hse-cat1
```

Stacks every row of `output/nen_viruses.csv` and then every row of `output/ICTV_cat1.csv`. The tables are not joined on virus name. HSE rows are labelled `HSE`. Category 1 rows are labelled `Cat1`. For an HSE row, ICTV family, species, kingdom, and the raw GenBank cell come from the VMR lookup of `NEN virus`. A blank `NEN virus` is not looked up.

The file written to `output/HSE-virus_Cat1-virus_merged.csv` is that stack sorted by ICTV genus ascending, then hazard group `4`, `3*`, `3`, `2`, `1`, then Schedule 5 `1` then `0`. Rows that share those three values keep their stack order. A hazard group or Schedule 5 value outside those lists is an error.

Flags: `--nen`, `--cat1`, `--vmr`, `--out`.

### 6. Download NCBI FASTA

```bash
export NCBI_EMAIL="name@example.com"
python -m virus_redteaming fetch-ncbi-fasta
```

Reads the `GenBank accessions` column of `output/HSE-virus_Cat1-virus_merged.csv`. A blank cell is skipped and counted. A cell may hold several segments separated by `;`, each shaped `label: accession`. A trailing coordinate such as `(1.2341)` is removed. Every distinct accession is fetched from NCBI nuccore as FASTA and written to `output/NCBI_fasta/{accession}.fasta`.

A file already in that directory is reused when it is one non-empty FASTA record whose header matches the accession. The command prints each path it wrote, then the blank-row count, the cached count, and the fetched count. There is no length cutoff on this command.

`NCBI_EMAIL` must be set and must not contain whitespace. A missing email exits `2`. A bad table or a failed fetch exits `1`. `--csv` and `--out` override the merged table and the FASTA directory.

### 7. Send sequences to Claude

```bash
python -m virus_redteaming claude-red-team
```

This command does not call NCBI. It reads `output/HSE-virus_Cat1-virus_merged.csv` and the FASTA files already in `output/NCBI_fasta`.

For each row:

- A blank `ICTV virus` and a blank `NCBI accession` are skipped. No output row is written.
- A named virus with a blank accession is written with `Claude response` set to `no sequence`. Claude is not called.
- Otherwise the accession is the text before the first `;`, stripped. Later segments in that cell are not sent. The FASTA body is copied to `output/claude_red-team_sequences/{accession}.txt` and uploaded as `sequence.txt`.

Two calls run for each uploaded sequence. The second starts only after the first returns a completed reply with at least one non-empty line. Each call waits 3 minutes. An empty reply or a timeout is stored as `no response`, and the second call is not sent. Calls run 20 at a time.

The virus name, family, genus, hazard group, and Schedule 5 stay in the output row. They are not placed in the prompt, the uploaded file, the upload filename, or the log. The log is `output/claude_red-team.log`.

The output header is:

```text
ICTV virus,Claude response,ICTV family,ICTV genus,Human pathogen hazard group,Schedule 5,Secondary structure
```

A missing `ANTHROPIC_API_KEY` exits `2`. The key is read from the environment or from `.env`. Other failures exit `1`. Flags: `--csv`, `--fasta`, `--sequences`, `--out`.

## Clinical FASTA workflow

This path does not use the merged table or `output/NCBI_fasta`. It searches NCBI nucleotide by virus name, then downloads the hits that pass a length cutoff.

Prepare two files:

- `output/genes.csv`, a UTF-8 CSV with a header cell exactly `Virus`. Other columns are ignored. A blank `Virus` cell is skipped.
- `output/search.txt`, exactly one non-empty line. The word `or`, with spaces on both sides, splits that line into alternatives. The line must not contain `"`, `[`, `]`, `(`, or `)`.

The query filename must be a bare name under `output/`. The default name is `genes.csv`.

```bash
export NCBI_EMAIL="name@example.com"
python -m virus_redteaming.clinical_fasta search
python -m virus_redteaming.clinical_fasta download
python -m virus_redteaming.clinical_fasta parse
```

`search` queries nuccore with the quoted `Virus` cell, one alternative from `output/search.txt`, and a length range. It keeps the first 5 accessions NCBI returns for each virus and writes `output/accessions.csv`. A virus with no hits is printed to stderr. The command exits `1` when any virus missed.

`download` reads the `Accession` column and writes one FASTA file under `output/clinical_genes/` for each distinct accession whose sequence is longer than 7000 bp. `--min-length` changes that cutoff for one run.

`parse` reads `output/accessions.csv` and `output/clinical_genes/`, then writes `output/accession_criteria.csv` and `output/NCBI_representative_seq.csv`.

`run` performs search, download, and parse in that order. A search miss does not stop the later steps, and the command still exits `1` when any virus missed. A bad `NCBI_EMAIL` exits `2`.

## Tests

```bash
pytest
```

Generated tables under `output/` are not required for the default test run. Commands that talk to NCBI or Claude are marked and stay skipped until the matching environment variable is set.

## Design

The index of specs and ADRs is `design/README.md`. The build notes for this workflow are:

| Step | Spec |
| --- | --- |
| Approved List parse | `design/specs/spec.redteam.md` |
| Schedule 5 | `design/specs/spec.schedule5.md` |
| Category 1 | `design/specs/spec.cat1.md` |
| VMR accessions | `design/specs/spec.nen_accession.md` |
| HSE and Category 1 merge | `design/specs/spec.hse_cat1_merge.md` |
| NCBI FASTA for the merged table | `design/specs/spec.ncbi_fasta.md` |
| Claude red-team | `design/specs/spec.claude-harness.md` |
| Clinical FASTA search | `design/specs/spec.NCBI.md` |

## Agent entry points

| Harness | File |
| --- | --- |
| Claude Code | `CLAUDE.md` |
| Cursor | `AGENTS.md` and `.cursor/rules/` |
| Canonical rules | `constitution/CONSTITUTION.md` |
