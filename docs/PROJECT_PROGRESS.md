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
| **Current Version** | 1.1.0 |
| **Current Sprint** | Sprint 2 — Parser correctness & data-quality hardening |

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
| OI-1 | **Case number parser needs redesign.** Regex `^[A-Z]\d{3}-\d{3}$` rejects valid 2-digit IDs like `A52-029`. Affects 173 records. | 🔴 High | Fix documented in Decisions Log. Needs comparison run to confirm improvement before merging. |
| OI-2 | **TM recovery from filenames** — if the folder name lacks a TM No, attempt to extract it from documents inside the folder. | 🟡 Medium | Future sprint. |
| OI-3 | **Submission integration** — connect to the IP Office submission API or filing portal. | 🟡 Medium | Future sprint. |
| OI-4 | **Merge engine** — deduplicate and merge records across multiple root folders (`1 ALL CLIENTS` + `2 CONSULTANTS`). | 🟡 Medium | `2 CONSULTANTS` not yet scanned. |
| OI-5 | **Dashboard** — web UI over the exported data for non-technical staff. | 🟢 Low | Future sprint. |
| OI-6 | **`2 CONSULTANTS` folder not yet validated.** Only `1 ALL CLIENTS` was scanned in the first run. | 🟡 Medium | Pass `--consultants-id FOLDER_ID` on next run. |

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
**Bug:** `parse_case_folder()` uses `re.match(r'^[A-Z]\d{3}-\d{3}$', part)` which
requires exactly 3 digits before the dash. Real Brandex folders use both 3-digit
(`A001-001`) and 2-digit (`A52-029`, `A54-005`) prefixes. 173 case folders are
affected — they have a valid TM No and Class but an empty Case # in exports.  
**Correct fix (not yet applied):**
```python
# Change in parse_case_folder() / diagnose_case() in main.py:
re.match(r'^[A-Z]\d{2,3}-\d{3}$', part)   # was: r'^[A-Z]\d{3}-\d{3}$'
```
**Validation step required before applying:** Run `batch_export.py` on `sample_drive/`
before and after, then run `compare_outputs.py` to confirm record counts increase and
no regressions appear.

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

**Previous behaviour:** missing TM No was treated as a failure (`is_failure = not case_no or not tm_no`), which contradicted BR-2.  
**Reason:** Business rules BR-2 and BR-3 explicitly state that TM No and Class code are optional in folder names; NTN and similar case types may never have a TM No; the record should always be generated. The validator must mirror `main.py`'s actual behaviour, not impose stricter rules.  
**Consequence:** On future runs, failure counts will be lower and warning counts will be higher relative to the first run (which used the stricter logic). The first run's `validation_failures.csv` is annotated accordingly — some rows listed as "failures" are correctly re-classified as "warnings" under the corrected rules.

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

## Next Sprint — Sprint 2 Tasks

> Replace this section at the start of each sprint. Archive the previous list as a
> completed sprint block above.

1. **[OI-1] Fix the 2-digit Case Number regex in `main.py`.**
   - Change `\d{3}` to `\d{2,3}` in `parse_case_folder()`.
   - Run `batch_export.py sample_drive before_fix` → apply fix →
     `batch_export.py sample_drive after_fix` → `compare_outputs.py`.
   - Confirm record count increases, no regressions on 3-digit IDs.

2. **[OI-6] Run `validate_drive.py` against `2 CONSULTANTS` folder.**
   - Pass `--consultants-id <FOLDER_ID>` (ID already found in prior session:
     `1Ke_B9vI_DdiiXPTTCBDtS4Ny6l73kIBU`).
   - Merge results with `1 ALL CLIENTS` report for a combined data-quality picture.

3. **[OI-4] Investigate duplicate records (26 found).**
   - Open `export/validation_failures.csv`, filter by duplicate composite key.
   - Determine whether duplicates are folder-naming errors or genuine data issues.
   - Document findings in this file under a new Decisions Log entry.

4. **Update `PROJECT_PROGRESS.md`** after each task above is confirmed complete.
