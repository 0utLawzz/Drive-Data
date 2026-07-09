# PROJECT BIBLE — Drive Folders List

> **Purpose:** the single reference document for what this project is, how it is
> structured, and which rules govern its behaviour. Read this before touching
> parsing logic. For a chronological log of what happened and when, see
> `docs/PROJECT_PROGRESS.md`. This file describes the *current state* of the
> system; PROJECT_PROGRESS.md describes *how it got there*.

---

## 1. What this project does

A CLI tool for a trademark law firm (Brandex). It scans a Google Drive–mirrored
folder tree organised as:

```
<root>/                          e.g. "1 ALL CLIENTS" or "2 CONSULTANTS"
  <client folder>/                e.g. "A-001 Smith & Associates"
    <case folder>/                e.g. "A001-001 Brand Name 123456 C01"
      <document files>            e.g. "TM-1 filed.pdf", "ACK 21-06-2024.pdf"
```

Folder *names* — not file contents — encode the structured data: client
number, client name, case number, case name, TM (trademark) number, and class
code. The tool parses these names, tick-marks which document categories are
present in each case folder, and exports the result to Google Sheets and/or
local Excel/CSV.

## 2. Two parsing engines

| Engine | Location | Status | Use |
|---|---|---|---|
| **V1 (legacy)** | `main.py` (`parse_client_folder`, `parse_case_folder`, `extract_full_case_name`) | Production default | Interactive CLI (`python main.py`), default engine everywhere |
| **V2 (token-based)** | `parser_v2/` package | Built & validated this sprint, **not yet promoted to production** | Opt-in via `batch_export.py --engine v2`; used by `validate_parser_v2.py` |

**Why two engines coexist:** `main.py` is never modified except for a
confirmed, isolated, reviewed bug fix (see docs/PROJECT_PROGRESS.md decision
2026-07-09-A). Parser V2 was built as a fully additive module so it could be
validated against real data with zero risk to the working production tool.
Promoting V2 to replace V1 in `main.py` is a deliberate future decision (OI-7
in docs/PROJECT_PROGRESS.md), not an automatic consequence of building it.

## 3. Parser V2 architecture (token-based)

```
parser_v2/
  tokens.py       — Token, TokenType (CLIENT_NO, CASE_NO, TM_NO, CLASS, DATE, WORD, NUM, OTHER)
  tokenizer.py     — tokenize(text) -> list[Token]; classification regex, ordered specific -> general
  rules.py         — classify_case_severity(): applies BR-2/BR-3/BR-5 (failure vs warning)
  parser.py        — parse_client_folder / parse_case_folder / extract_full_case_name / diagnose_case / diagnose_client
  directory.py     — process_directory(): same output shape as main.py, walks a directory tree
  __init__.py      — re-exports the above with the same names as main.py, for drop-in use
```

**Why tokenize first, then extract:** the legacy parser applies positional
regexes to raw string splits inline, in a single pass, with brittle assumed
ordering. Token-based parsing separates two concerns:

1. **What is this word?** (tokenizer.py — a pure classification function,
   independently testable, single source of truth for "what does a Case #
   look like".)
2. **What do these words mean together?** (parser.py — walks the token
   stream looking for anchors like CASE_NO/TM_NO regardless of position.)

This makes it possible to fix systemic bugs in one place (the tokenizer's
CASE_NO regex, or the case-name extraction path) with the fix automatically
applying everywhere, instead of hunting down every regex site that encodes
the same assumption.

### Confirmed business rules implemented by Parser V2

See `docs/PROJECT_PROGRESS.md` → "Confirmed Business Rules" for the
authoritative table (BR-1..BR-7) and their evidence sources. Summary as
implemented in `parser_v2/rules.py`:

- **BR-1/BR-2/BR-5:** TM Number is optional; missing TM No is a **warning**,
  never a failure — including NTN/administrative case types that structurally
  never carry a TM No.
- **BR-3:** Missing Class code is a **warning**, never a failure.
- **BR-6:** Every case folder produces a record, even with zero files inside
  (`parser_v2/directory.py` groups by composite key exactly like `main.py`).
- **Severity classification (decision 2026-07-09-C2):** `is_failure` = missing
  Case # only. `is_warning` = missing TM No and/or Class code, provided Case #
  was found. `is_ok` = nothing missing. Applied identically by
  `parser_v2.parser.diagnose_case()`.

### Confirmed bug fix #1: 2-digit Case Numbers (OI-1)

`tokenizer.py`'s `_CASE_NO_RE` is `^[A-Z]\d{2,3}-\d{3}$` (2- **or** 3-digit
prefix), not the legacy `^[A-Z]\d{3}-\d{3}$` (3-digit only). Real Brandex
folders use both (`A001-001` and `A52-029`). This single change recovered the
Case # on **210 of 3,454** real case folders in the Sprint 3 live-Drive
validation run, with zero regressions.

### Confirmed bug fix #2: case_name truncation for TM-less folders

`main.py`'s `extract_full_case_name()` only runs when a TM No is present (it
early-returns `""` otherwise), so V1 falls back to a single captured WORD
token as `case_name` for any TM-less folder — silently dropping the rest of
the name (e.g. `"BEHTREEN TEA"` → V1 case_name `"BEHTREEN"`). V2's
`parse_case_folder` extracts the full multi-word name unconditionally. This
affected **130 of 3,454** real case folders. Discovered during Sprint 3 live
validation once the comparator was widened to check `case_name` (not only
`case_no`/`tm_no`/`class_code`) — see docs/PROJECT_PROGRESS.md decision
2026-07-09-G.

Both fixes live only in Parser V2 and have **not** been applied to `main.py`
— see §2 above and OI-7 in docs/PROJECT_PROGRESS.md.

### Known limitation: multi-TM-number folders

Two folders in the live dataset contain **two** 6-digit numbers (dispute /
rectification cases, e.g. `"... MAAM VS POWER MAAM 317643 V 713643"`,
`"LOGO 628734 VS LOGGO 701314"`). V1's loop overwrites `tm_no` on every
match, so it keeps the *last* 6-digit token found. V2 deliberately keeps the
*first* token found (first-match-wins is the documented, deterministic
convention for every other field). Neither behaviour is objectively correct
— the underlying folder name is genuinely ambiguous about which number is
primary. This affects 2 of 3,454 real case folders (0.06%); flagged in the
validation report for manual review rather than silently resolved either way
(tracked as OI-8 — needs a business decision, not a parser heuristic).

### Sprint 3 validation summary (live Brandex dataset, 3,454 case folders)

| | Identical | Case # recovered (OI-1) | case_name fixed | Regressions | Ambiguous (OI-8) |
|---|---|---|---|---|---|
| Count | 3,112 | 210 | 130 | **0** | 2 |

Full detail in `export/parser_v2_validation_report.md` (regenerated by
`validate_parser_v2.py`, gitignored — regenerate by re-running the script).

## 4. Non-goals for this sprint

- **Submission integration** (OI-3 — connecting to an IP Office filing
  portal/API) is explicitly out of scope. Do not start it.
- Parser V2 has **not** been promoted into `main.py` or made the default
  engine. That is a deliberate follow-up decision (OI-7 in
  docs/PROJECT_PROGRESS.md), not an oversight.

## 4a. Sprint 4 — Online Drive inventory (`drive_api/` + `inventory.py`)

**Why:** the original tool (and `validate_drive.py`) required a locally
mounted / Desktop-synced copy of the Drive tree for local-path scanning, or
was validation-only. Sprint 4's goal is a reliable, online, metadata-only
inventory of the *entire* live Drive structure to understand real data shape
before further parser/automation work — not to improve parsing further.

```
Google Drive API → Folder ID (settings.json) → drive_api/ → inventory.py → export/
```

- `drive_api/` is the **only** place that imports `googleapiclient` /
  `google.oauth2`. Everything else (parser_v2, inventory.py) works with the
  plain `DriveFolder`/`DriveFile` objects in `drive_api/models.py`.
- `drive_api/scanner.py` (live Drive) and `drive_api/local_source.py` (local
  directory, used only for offline smoke-testing against `sample_drive/`)
  return the **identical** object shapes — `parser_v2` and `inventory.py`
  never know or care which source produced a given record. This mirrors the
  same "swap the engine, not the caller" principle used for Parser V1/V2.
- Folder IDs (`clients_folder_id`, `consultants_folder_id`) live in
  `settings.json` at the project root — never hardcoded in Python, and safe
  to commit (no secrets). `credentials.json` (the Service Account key)
  remains gitignored as before.
- `inventory.py` parses folder names with **Parser V2 only** (not V1) —
  Sprint 4 is a downstream consumer of the parser, not a parser change; using
  the validated, strictly-better engine (§3) for a fresh dataset extraction
  avoids re-introducing V1's known Case #/case_name bugs into new output.
- Output is metadata only for files (id, name, extension, MIME type, size,
  timestamps, parent, Drive URL) — file *contents* are never read.
- `inventory_report.md` is **descriptive only**: it reports data-quality
  signals (missing TM/Class, empty case folders, duplicate TM numbers,
  largest case folder, average files per case) without attempting to fix or
  normalise anything, consistent with how `validate_drive.py` treats
  discovered issues (decision 2026-07-09-B).

## 5. Key files

| File | Purpose |
|---|---|
| `main.py` | Original interactive CLI — legacy (V1) parsing, pattern matching, Sheets/local export. Modify only for confirmed, reviewed bug fixes. |
| `parser_v2/` | Token-based parser (V2), additive, opt-in. See §3. |
| `batch_export.py` | Non-interactive runner. `--engine v1\|v2` selects the parsing engine (default v1). |
| `compare_outputs.py` | Diffs two CSV/Excel exports on composite key; used to confirm V1 vs V2 equivalence on `sample_drive`. |
| `validate_drive.py` | Full live-Drive validator (folders + files) for the legacy engine. Unmodified this sprint. |
| `validate_parser_v2.py` | Lightweight live-Drive comparator: V1 vs V2 diagnosis on every real case folder name (case_no, tm_no, class_code, case_name). Folder-names only (no file listing) — much faster than `validate_drive.py`. |
| `sample_drive/` | 7 synthetic clients / 15 case folders for fast local regression checks. |
| `docs/PROJECT_PROGRESS.md` | Append-only chronological log: milestones, decisions, open issues, sprint history. |
| `PROJECT_BIBLE.md` | This file — current-state architecture & rules reference. |
| `credentials.json` | Google Service Account key, gitignored. Required for `validate_drive.py` / `validate_parser_v2.py` / Sheets upload / `inventory.py --source drive`. |
| `drive_api/` | Sprint 4 online Drive API access layer (auth, config, scanner, shared models, local-source adapter). See §4a. |
| `inventory.py` | Sprint 4 entry point: online client/case/file inventory extraction + CSV/XLSX/Markdown report export. See §4a. |
| `settings.json` | Sprint 4 config: Drive root folder IDs and Service Account key path. Not gitignored (no secrets). |

## 6. Glossary

- **Case folder** — one trademark case; produces one exported record.
- **Client folder** — one client (law firm's customer); contains 1+ case folders.
- **TM No** — 6-digit trademark application/registration number; optional at filing time (BR-1).
- **Class** — a Nice Classification class code, `C` + 1-2 digits (e.g. `C01`, `C29`).
- **Composite key** — `(CLIENT NUMBER, CASE #, TM NO, CLASS)`; used for duplicate detection and diff comparisons (BR-4, BR-7).
- **Parse failure vs. parse warning** — a failure means the record cannot be reliably identified (missing Case #); a warning means the record was generated but is missing an optional field (TM No and/or Class).
