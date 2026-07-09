# Project Progress Tracker

> **How to use this file:**
> Never overwrite previous entries. Append new milestones, decisions, and sprint updates
> at the bottom of their respective sections so every AI session immediately understands
> the full project history.

---

## Project Overview

| Field | Value |
|---|---|
| **Goal** | Scan Google Drive–mirrored folder structures for a trademark law firm, extract structured client/case/TM data from folder names, and export to Google Sheets or local Excel/CSV. Secondary goal: validate parser correctness against the live Brandex Drive dataset without modifying production code. |
| **Current Version** | 1.2.0 |
| **Current Sprint** | Sprint 4 — Online Drive inventory (`drive_api/` + `inventory.py`) |

---

## Completed Milestones

### ✅ Project Import & Environment Setup
*Completed: 2026-07-09*

- Imported original Drive Folders List CLI tool from GitHub into Replit.
- Verified Python 3.12 runtime, installed all dependencies (`pandas`, `openpyxl`,
  `gspread`, `google-auth`, `google-api-python-client`).
- Confirmed `main.py` interactive CLI runs end-to-end with local paths.
- Created `sample_drive/` with 7 synthetic clients and 15 realistic case folders
  for offline regression testing.

### ✅ Modular Architecture
*Completed: 2026-07-09*

- Established strict separation of concerns:
  - `main.py` — original interactive CLI, **never modified unless a confirmed bug is found**.
  - `batch_export.py` — non-interactive runner; imports `process_directory` directly
    from `main.py` so any future refactor is automatically reflected.
  - `compare_outputs.py` — pure diff/comparison tool, no parsing logic.
  - `validate_drive.py` — real-world Drive API validator, read-only with respect to
    production code.
- All output artefacts written to `export/` (gitignored).

### ✅ Batch Exporter (`batch_export.py`)
*Completed: 2026-07-09*

- Non-interactive runner: `python batch_export.py <drive_path> <prefix> [--max N]`.
- Imports `process_directory` from `main.py` — no logic duplication.
- Writes `export/<prefix>.csv` and `export/<prefix>.xlsx`.
- Used as the baseline-capture step in the refactor validation workflow.

### ✅ Comparison Tool (`compare_outputs.py`)
*Completed: 2026-07-09*

- Diffs two CSV/Excel exports on composite key `(CLIENT NUMBER, CASE #, TM NO, CLASS)`.
- `DATE ADDED` intentionally excluded from comparison key (timestamps differ per run).
- Categorises records as Added / Removed / Changed / Identical.
- Warns on duplicate composite keys in either input file.
- All user-derived values HTML-escaped before output.
- Produces `export/comparison_report.html` (colour-coded) and `export/comparison_report.csv`.

### ✅ Real-World Drive Validator (`validate_drive.py`)
*Completed: 2026-07-09*

- Connects to Google Drive API v3 using a Service Account (`credentials.json`).
- Traverses the live Brandex `1 ALL CLIENTS` folder hierarchy in parallel
  (`ThreadPoolExecutor`, default 12 workers; each worker holds its own Drive
  service instance via thread-local storage to avoid connection sharing across threads).
- Collects 14 data-quality metrics per run.
- Generates top-10 unrecognised folder-naming pattern report with structural
  token signatures (e.g. `[CASE_NO] [UPPER] [TM_NO] [CLASS]`) and per-pattern
  improvement suggestions.
- Produces four output artefacts in `export/`:
  `validation_report.html`, `validation_report.md`,
  `validation_warnings.csv`, `validation_failures.csv`.
- **No project code modified.** Confirmed bugs are documented in the generated
  reports only.

### ✅ First Real-World Validation Run
*Completed: 2026-07-09*

Results against live Brandex `1 ALL CLIENTS` folder (63 clients, 871 cases):

| Metric | Count | % of Cases |
|---|---|---|
| Cases fully parsed | 488 | 56.0% |
| Parse failures | 367 | 42.1% |
| Parse warnings | 16 | 1.8% |
| Duplicate records | 26 | — |
| Empty case folders | 32 | — |
| Missing TM Number | 194 | 22.3% |
| Missing Class code | 125 | 14.4% |
| Missing Case Number | 214 | 24.6% |

**Confirmed parser bug discovered:** See Decisions Log entry 2026-07-09-B.

### ✅ Parser V2 — Token-Based Architecture
*Completed: 2026-07-09*

- Built `parser_v2/` as a fully additive package (tokens.py, tokenizer.py,
  rules.py, parser.py, directory.py) — `main.py` was **not modified**.
- Public API mirrors `main.py` 1:1 (`parse_client_folder`, `parse_case_folder`,
  `extract_full_case_name`, `process_directory`) so it is a drop-in engine
  swap for any caller.
- Implements BR-1, BR-2, BR-3, BR-5, BR-6 explicitly in `parser_v2/rules.py`,
  and bakes in the OI-1 fix (2-digit Case # prefix) at the tokenizer level.
- Severity classification (`is_failure` = missing Case # only; `is_warning`
  = missing TM No/Class) matches decision 2026-07-09-C2 exactly.
- Added `batch_export.py --engine {v1,v2}` so either engine can be run
  non-interactively without touching call sites.
- Created `PROJECT_BIBLE.md` as the current-state architecture & rules
  reference (complements this append-only progress log).

### ✅ Parser V2 Validation
*Completed: 2026-07-09*

- **sample_drive/ (15 records):** `compare_outputs.py` on V1 vs V2 output —
  0 added, 0 removed, 0 changed. Fully identical.
- **Live Brandex dataset (both `1 ALL CLIENTS` and `2 CONSULTANTS`, 3,454
  real case folders):** ran `validate_parser_v2.py`, a lightweight
  folder-names-only comparator (no file listing, so much faster than the
  full `validate_drive.py` run). Compares case_no, tm_no, class_code, AND
  case_name field-by-field between engines.
  - V1: 2,790 failures / 172 warnings / 492 OK.
  - V2: 2,580 failures / 216 warnings / 658 OK.
  - **3,112 / 3,454 identical output. 210 Case # recoveries (OI-1). 130
    case_name-truncation fixes (v1's `extract_full_case_name()` only runs
    when a TM No is present, so it drops words for TM-less folders — v2
    always extracts the full name). 0 regressions. 2 pre-existing
    multi-TM-number edge cases flagged for manual review (OI-8), not
    silently resolved either way.**
  - Full report: `export/parser_v2_validation_report.md`.
- Confirmed Parser V2 is a strict improvement over the legacy engine on the
  real dataset with no observed backward-compatibility breaks.

### ✅ Sprint 4 — Online Drive Inventory (`drive_api/` + `inventory.py`)
*Completed: 2026-07-09*

- Built `drive_api/` as the sole boundary for Google Drive API code
  (`auth.py` Service Account + OAuth fallback, `config.py` settings.json
  loader, `scanner.py` live traversal, `local_source.py` local-directory
  adapter, `models.py` shared `DriveFolder`/`DriveFile` objects).
- Removed the local-mount/Desktop-sync dependency for this workflow:
  scanning now goes `Google Drive API → Folder ID → Python`, configured via
  `settings.json` (`clients_folder_id`, `consultants_folder_id`,
  `credentials_path`) instead of hardcoded paths.
- `inventory.py` extracts full client/case/file metadata (folder IDs,
  names, parents, client code/name, case #/name/TM No/class/case type,
  created/modified timestamps, file extension/MIME/size/Drive URL) using
  **Parser V2** for folder-name parsing — metadata only, file contents are
  never read.
- Exports `export/clients.csv`, `export/cases.csv`, `export/files.csv`,
  `export/drive_inventory.xlsx` (3 worksheets), and a descriptive-only
  `export/inventory_report.md` (totals, case types, missing TM/Class,
  empty case folders, duplicate TM numbers, largest case folder, average
  files per case).
- `drive_api/local_source.py` lets `inventory.py --source local` run
  offline against `sample_drive/` for smoke-testing, returning identical
  object shapes to the live scanner so neither the parser nor the report
  code needs to know the data source (verified: 7 clients / 15 cases / 67
  files extracted correctly from `sample_drive/`).
- No parser optimization work was done this sprint (explicitly out of
  scope per direction); OI-3 (Submission Integration) and OI-5 (Dashboard)
  were not started.

---

## Confirmed Business Rules

> These rules were established through codebase analysis and real-world validation.
> They govern parser behaviour and must be preserved across refactors.

| # | Rule | Source |
|---|---|---|
| BR-1 | **TM Number is optional in folder names.** Not every case has a TM number at filing time. | Domain knowledge + real data |
| BR-2 | **Missing TM Number is a warning, not a parse failure.** The record is still generated; the TM No field is left blank. | `main.py` behaviour + validation run |
| BR-3 | **Missing Class code is a warning, not a parse failure.** Same treatment as missing TM No. | `main.py` behaviour + validation run |
| BR-4 | **Duplicate detection should primarily use TM Number** as the most stable unique identifier for a trademark case. Composite key `(CLIENT NUMBER, CASE #, TM NO, CLASS)` is used in the comparison tool. | Architectural decision 2026-07-09 |
| BR-5 | **NTN and similar administrative case types may never have a TM Number.** Folders like `A51-016 M TAHIR NTN` are valid records, not naming errors. | Real data observation 2026-07-09 |
| BR-6 | **Empty case folders are still counted as records.** `main.py` adds every case folder to `case_groups` regardless of file contents; the validator mirrors this. | `main.py` code audit 2026-07-09 |
| BR-7 | **`DATE ADDED` is excluded from comparison keys.** Timestamps differ per run and must not trigger false positives in diff reports. | `compare_outputs.py` design 2026-07-09 |

---

## Open Issues

| ID | Issue | Priority | Notes |
|---|---|---|---|
| OI-1 | **Case number parser needs redesign.** Legacy regex only matched a 3-digit prefix before the dash, rejecting valid 2-digit IDs like A52-029. Affects 173+ records. | ✅ Resolved in Parser V2 | Fix implemented in `parser_v2/tokenizer.py` (2- or 3-digit prefix accepted) and validated against the full live dataset (210 records recovered, 0 regressions). **Not yet applied to `main.py`** — V1 remains the production engine until V2 is promoted (new: OI-7). |
| OI-2 | **TM recovery from filenames** — if the folder name lacks a TM No, attempt to extract it from documents inside the folder. | 🟡 Medium | Future sprint. |
| OI-3 | **Submission integration** — connect to the IP Office submission API or filing portal. | 🟡 Medium | Future sprint. Explicitly not started in Sprint 3 per direction. |
| OI-4 | **Merge engine** — deduplicate and merge records across multiple root folders (`1 ALL CLIENTS` + `2 CONSULTANTS`). | 🟡 Medium | Still open — carried to Sprint 4. |
| OI-5 | **Dashboard** — web UI over the exported data for non-technical staff. | 🟢 Low | Future sprint. |
| OI-6 | **`2 CONSULTANTS` folder not yet validated.** Only `1 ALL CLIENTS` was scanned in the first run. | ✅ Resolved | Sprint 3's `validate_parser_v2.py` run covered both `1 ALL CLIENTS` and `2 CONSULTANTS` (3,454 case folders total). |
| OI-7 | **Promote Parser V2 into `main.py`** (replace the legacy engine now that it's validated) — requires a deliberate cutover decision, re-running full validation post-cutover, and a version bump. | 🟡 Medium | Future sprint. Do not do this silently; V1 stays the production default until explicitly promoted. |
| OI-8 | **Multi-TM-number folders (2 known cases)** — folder names containing two 6-digit numbers (dispute/rectification cases) are ambiguous about which is the primary TM No. | 🟢 Low | See PROJECT_BIBLE.md §3 "Known limitation". Needs a human/business decision, not a parser heuristic. |

---

## Decisions Log

> Append new entries at the bottom. Never remove or modify existing entries.

---

### 2026-07-09-A — `batch_export.py` imports from `main.py` directly

**Date:** 2026-07-09
**Decision:** `batch_export.py` imports `process_directory` from `main.py` rather than
duplicating parsing logic.
**Reason:** Any refactor to `main.py` is automatically reflected in batch exports and
comparison runs without needing to keep two copies of the logic in sync.
**Consequence:** `main.py` must remain importable (no top-level side effects outside
`if __name__ == "__main__"`). Verified — it is.

---

### 2026-07-09-B — Confirmed parser bug: 2-digit Case Numbers not recognised

**Date:** 2026-07-09
**Decision:** Bug documented in validation reports only. `main.py` was NOT modified.
**Bug:** `parse_case_folder()` only matched Case Numbers with exactly 3 digits before
the dash (e.g. `A001-001`). Real Brandex folders use both 3-digit and 2-digit prefixes
(`A52-029`, `A54-005`). 173 case folders are affected — they have a valid TM No and
Class but an empty Case # in exports.
**Correct fix (documented, not applied to main.py in Sprint 2):** widen the Case #
pattern to accept a 2- or 3-digit prefix.
**Validation step required before applying:** Run `batch_export.py` on `sample_drive/`
before and after, then run `compare_outputs.py` to confirm record counts increase and
no regressions appear. (Sprint 3 performed this validation inside Parser V2 — see
decisions 2026-07-09-E and 2026-07-09-F.)

---

### 2026-07-09-C — Parallel Drive traversal with thread-local service instances

**Date:** 2026-07-09
**Decision:** `validate_drive.py` uses `ThreadPoolExecutor` (default 12 workers).
Each worker thread builds its own Drive API service instance via `threading.local()`
rather than sharing one.
**Reason:** `googleapiclient` HTTP connections are not thread-safe. Sharing one service
object across threads causes silent request failures or connection pool exhaustion.
Sequential traversal of 848 client folders would take ~96 minutes; parallel traversal
completed 63 accessible folders in 427 seconds.
**Consequence:** Worker count is tunable via `--workers N` CLI argument. Duplicate-key
detection is deliberately kept in the main thread after all workers finish to avoid
needing locks around the `seen_keys` dict.

---

### 2026-07-09-C2 — Validator severity classification aligned with business rules

**Date:** 2026-07-09
**Decision:** `diagnose_case()` in `validate_drive.py` updated so that:
- `is_failure` = **missing Case # only**
- `is_warning` = **missing TM No and/or missing Class code** (record still generated)

**Previous behaviour:** missing TM No was treated as a failure, which contradicted BR-2.
**Reason:** Business rules BR-2 and BR-3 explicitly state that TM No and Class code are
optional in folder names; NTN and similar case types may never have a TM No; the record
should always be generated. The validator must mirror `main.py`'s actual behaviour, not
impose stricter rules.
**Consequence:** On future runs, failure counts will be lower and warning counts will be
higher relative to the first run (which used the stricter logic). Parser V2 (Sprint 3)
implements this exact same classification in `parser_v2/rules.py`.

---

### 2026-07-09-D — `docs/PROJECT_PROGRESS.md` established as persistent project log

**Date:** 2026-07-09
**Decision:** Created `docs/PROJECT_PROGRESS.md` as the single source of truth for
milestones, business rules, open issues, and architectural decisions across all sessions.
**Reason:** AI sessions have no persistent memory between conversations. This file
gives any future session immediate context without re-reading all source files.
**Convention:** Append only. Never overwrite existing entries. Every completed milestone,
confirmed business rule, and architectural decision must be recorded here before the
session ends.

---

### 2026-07-09-E — Parser V2 built as an additive package, not a `main.py` rewrite

**Date:** 2026-07-09
**Decision:** Sprint 3's token-based parser was built entirely inside a new
`parser_v2/` package. `main.py` was not touched.
**Reason:** `main.py` is the production tool actively used by the firm.
Rewriting its parsing logic in place would risk breaking a working tool with
no rollback path mid-sprint. Building V2 additively allowed full validation
against the real 3,454-record Brandex dataset with zero production risk.
**Consequence:** Two engines now coexist (see PROJECT_BIBLE.md §2). `main.py`
is unaffected by this sprint; OI-1 remains open **for the production engine**
even though it is fixed in V2. Promoting V2 to production is tracked
separately as OI-7 and requires a deliberate future decision.

---

### 2026-07-09-F — Parser V2 validated against the full live Brandex dataset before commit

**Date:** 2026-07-09
**Decision:** Before finalizing Sprint 3, ran `validate_parser_v2.py` against
both live Drive roots (`1 ALL CLIENTS` and `2 CONSULTANTS`, 3,454 real case
folders total), comparing V1 and V2 output field-by-field.
**Reason:** "Validated against the Brandex dataset before committing" was an
explicit Sprint 3 requirement — sample_drive alone (15 records) cannot
surface systemic issues like the 2-digit Case # bug, which only appears at
scale in the real dataset.
**Consequence:** Any future engine change must re-run this comparator before
being trusted; regressions (V1 succeeded, V2 blanks a field) are a hard
blocker at 0 by design.

---

### 2026-07-09-G — Field-comparison scope corrected to include case_name; second real fix discovered

**Date:** 2026-07-09
**Decision:** `validate_parser_v2.py`'s comparison originally checked only
`case_no`, `tm_no`, and `class_code`, while its own report language implied a
full-field comparison. Widened the comparison to include `case_name` as well,
added a `case_name_fixed` bucket to the comparator, and regenerated
`export/parser_v2_validation_report.md` from a fresh run.
**Reason:** Caught during Sprint 3 code review — comparing a subset of fields
while claiming full comparison risks silently missing case_name extraction
regressions between engines.
**Finding:** the wider comparison surfaced a second real, pre-existing bug:
`main.py`'s `extract_full_case_name()` only runs when a TM No is present
(it early-returns `""` otherwise), so v1 falls back to a single captured
WORD token as case_name for any TM-less folder — silently dropping the rest
of the name. This affected 130 of 3,454 real case folders. Parser V2 does
not have this limitation (it extracts the full name unconditionally).
**Consequence:** Final validation metrics (`export/parser_v2_validation_report.md`):
3,112/3,454 identical, 210 Case # recoveries (OI-1), 130 case_name-truncation
fixes (new, not previously tracked as an open issue — documented directly as
resolved-in-V2 since it was found and fixed within the same sprint), 0
regressions, 2 remaining ambiguous multi-TM-number cases (OI-8). This bug is
**not** applied to `main.py`, consistent with decision 2026-07-09-E — it
stays fixed only in Parser V2 until OI-7 (promotion) is decided.

---

### 2026-07-09-H — Online Drive access isolated to `drive_api/`; parser stays source-agnostic

**Date:** 2026-07-09
**Decision:** All `googleapiclient`/`google.oauth2` usage for the new online
inventory workflow lives in `drive_api/`. `inventory.py` and `parser_v2`
consume only the plain `DriveFolder`/`DriveFile` objects defined in
`drive_api/models.py`; `drive_api/local_source.py` produces the identical
shape from a local directory (`sample_drive/`) for offline testing.
**Reason:** Sprint 4 direction explicitly required that "the parser should
not know whether data came from local folders or the Google Drive API."
Isolating the API boundary also means future auth changes (e.g. Service
Account → OAuth, or Shared Drive support) touch one module only.
**Consequence:** Folder-name parsing for the new inventory always uses
Parser V2 (not V1/`main.py`) — this is a new consumer of the already
validated engine, not a change to `main.py` or a decision to promote V2 into
production (OI-7 is unaffected and still open).

---

## Completed Sprint — Sprint 2 Tasks (archived)

1. ~~[OI-1] Fix the 2-digit Case Number regex in `main.py`.~~ **Superseded:**
   fixed in Parser V2 (`parser_v2/tokenizer.py`) instead of `main.py` directly —
   see decision 2026-07-09-E. Promoting the fix into `main.py` itself is now OI-7.
2. ~~[OI-6] Run `validate_drive.py` against `2 CONSULTANTS` folder.~~ **Done** —
   covered by `validate_parser_v2.py` in Sprint 3 (both roots, 3,454 case folders).
3. **[OI-4] Investigate duplicate records (26 found).** Still open — carried to Sprint 4.
4. Progress doc updated throughout Sprint 3 (this document).

---

## Completed Sprint — Sprint 4 Tasks (archived)

1. **Online Drive scanner (`drive_api/`)** — done. Service Account auth,
   `settings.json`-driven folder IDs, no local mount required. See milestone
   above and decision 2026-07-09-H.
2. **Full client/case/file metadata extraction (`inventory.py`)** — done.
3. **CSV + XLSX + Markdown report export** — done
   (`export/{clients,cases,files}.csv`, `export/drive_inventory.xlsx`,
   `export/inventory_report.md`).
4. **Documentation updates** — this file, `PROJECT_BIBLE.md`, `CHANGELOG.md`.

## Next Sprint — Sprint 5 Tasks

> Replace this section at the start of each sprint. Archive the previous list as a
> completed sprint block above.
>
> **Explicitly out of scope until directed otherwise: OI-3 Submission Integration.**

1. **Run `inventory.py` against the live Brandex Drive** and review
   `export/inventory_report.md` once real `clients_folder_id`/
   `consultants_folder_id` and `credentials.json` are provided — this
   sprint only validated the pipeline against `sample_drive/`.

2. **[OI-4] Investigate duplicate records (26 found in the first live-Drive run).**
   - Re-run `validate_drive.py` (full traversal, needed for file-based duplicate
     detection) or extend `validate_parser_v2.py` with duplicate-key tracking.
   - Determine whether duplicates are folder-naming errors or genuine data issues.
   - Document findings under a new Decisions Log entry.

3. **[OI-7] Decide whether/when to promote Parser V2 into production.**
   - Options: (a) swap `main.py` internals to import from `parser_v2`, (b) keep
     `main.py` frozen and make `parser_v2` the new entry point with its own CLI.
   - Requires stakeholder sign-off given `main.py` is actively used by the firm.
   - If promoted: re-run `validate_parser_v2.py`-style comparison as a post-cutover
     regression check, and bump the version.

4. **[OI-8] Resolve the multi-TM-number folder convention (2 known cases).**
   - Decide the business rule for folders with two 6-digit numbers (e.g. dispute
     records) — first-found, last-found, or flag for manual entry.
   - Encode the decision explicitly in `parser_v2/rules.py` once agreed, and add
     it to the Confirmed Business Rules table as BR-8.

5. **[OI-2] TM recovery from filenames** (if the folder name lacks a TM No,
   attempt to extract it from documents inside the folder) — still pending,
   unchanged from Sprint 1/2 backlog.

6. **Do not start OI-3 (Submission Integration)** until explicitly requested.
