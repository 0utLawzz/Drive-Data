# Brandex Drive — Validation Report

**Generated:** 2026-07-09 16:59:29  
**Duration:** 427.2s  
**Root folders:** 1 ALL CLIENTS

---

## Summary Statistics

| Metric | Count | % of Cases |
|---|---|---|
| Root folders scanned | 1 | — |
| Client folders scanned | 63 | — |
| Case folders scanned | 871 | — |
| Files scanned | 3321 | — |
| Records generated | 845 | — |
| **Cases fully parsed** | **488** | **56.0%** |
| Parse warnings | 16 | 1.8% |
| Parse failures | 367 | 42.1% |
| Duplicate records | 26 | — |
| Empty case folders | 32 | — |
| Missing TM Number | 194 | 22.3% |
| Missing Class code | 125 | 14.4% |
| Missing Case Number | 214 | 24.6% |
| Unrecognized client folders | 0 | — |

---

## Top 10 Unrecognised Folder Naming Patterns

| # | Pattern | Count | Examples | Suggested Improvement |
|---|---|---|---|---|
| 1 | `[OTHER] [UPPER] [UPPER] [TM_NO] [CLASS]` | 63 | A52-029 SOULFUL BITES 874479 C43; A52-030 CITY MOTORS 879555 C35 | TM No detected but Case # is missing — prepend the Case # (e.g. A001-001) before the case name. |
| 2 | `[OTHER] [UPPER] [TM_NO] [CLASS]` | 37 | A54-005 SERENE  869624 C5; A52-030 RIVER 851860 C7 | TM No detected but Case # is missing — prepend the Case # (e.g. A001-001) before the case name. |
| 3 | `[OTHER] [UPPER] [UPPER] [UPPER] [TM_NO] [CLASS]` | 27 | A54-006 PAKLAND PUBLIC SCHOOL 872936 C41; A54-001 BM SWEET SUPARI 773953 C30 | TM No detected but Case # is missing — prepend the Case # (e.g. A001-001) before the case name. |
| 4 | `[CASE_NO] [UPPER] [CLASS]` | 22 | A003-029 ASAR C32; A003-024 HEMERSIN C30 | Folder is missing: TM No (6 digits). |
| 5 | `[CASE_NO] [UPPER] [UPPER] [CLASS]` | 22 | A003-006 KHAN SALANTY C30; A039-015 HAK COSMETICS C3 | Folder is missing: TM No (6 digits). |
| 6 | `[CASE_NO] [UPPER] [UPPER]` | 13 | A003-028 BEHTREEN TEA; A003-055 FANTASTIC CP | Only Case # found — add 6-digit TM No and class code (e.g. C01) to the folder name so all fields can be extracted. |
| 7 | `[CASE_NO] [UPPER] [UPPER] [UPPER]` | 11 | A003-001 MULTIPAL REPLY MIX; A039-003 AMJAD ALI FBR | Only Case # found — add 6-digit TM No and class code (e.g. C01) to the folder name so all fields can be extracted. |
| 8 | `[CASE_NO] [UPPER] [UPPER] [UPPER] [UPPER]` | 10 | A003-049 TARIQ BANNU BEEF PULAO; A023-053 MINAL MALIK KHURAM ADV | Only Case # found — add 6-digit TM No and class code (e.g. C01) to the folder name so all fields can be extracted. |
| 9 | `[OTHER] [UPPER] [UPPER] [UPPER] [UPPER] [TM_NO] [CLASS]` | 10 | A54-003 CITY EDUCATION SCHOOL SYSTEM 869619 C41; A54-002 LAHORI GOLD SWEET SUPARI 773616 C30 | TM No detected but Case # is missing — prepend the Case # (e.g. A001-001) before the case name. |
| 10 | `[OTHER] [UPPER] [UPPER] [UPPER]` | 9 | A51-016 M TAHIR NTN; A51-015 IMRAN KHAN NTN | All-caps text with no structured codes — add Case # (e.g. A001-001), TM No (6 digits), and Class (e.g. C01). |

---

## ⚠️ Confirmed Parser Bug

**Bug:** `parse_case_folder()` in `main.py` uses the regex `^[A-Z]\d{3}-\d{3}# Brandex Drive — Validation Report

**Generated:** 2026-07-09 16:59:29  
**Duration:** 427.2s  
**Root folders:** 1 ALL CLIENTS

---

## Summary Statistics

| Metric | Count | % of Cases |
|---|---|---|
| Root folders scanned | 1 | — |
| Client folders scanned | 63 | — |
| Case folders scanned | 871 | — |
| Files scanned | 3321 | — |
| Records generated | 845 | — |
| **Cases fully parsed** | **488** | **56.0%** |
| Parse warnings | 16 | 1.8% |
| Parse failures | 367 | 42.1% |
| Duplicate records | 26 | — |
| Empty case folders | 32 | — |
| Missing TM Number | 194 | 22.3% |
| Missing Class code | 125 | 14.4% |
| Missing Case Number | 214 | 24.6% |
| Unrecognized client folders | 0 | — |

---

## Top 10 Unrecognised Folder Naming Patterns

| # | Pattern | Count | Examples | Suggested Improvement |
|---|---|---|---|---|
| 1 | `[OTHER] [UPPER] [UPPER] [TM_NO] [CLASS]` | 63 | A52-029 SOULFUL BITES 874479 C43; A52-030 CITY MOTORS 879555 C35 | TM No detected but Case # is missing — prepend the Case # (e.g. A001-001) before the case name. |
| 2 | `[OTHER] [UPPER] [TM_NO] [CLASS]` | 37 | A54-005 SERENE  869624 C5; A52-030 RIVER 851860 C7 | TM No detected but Case # is missing — prepend the Case # (e.g. A001-001) before the case name. |
| 3 | `[OTHER] [UPPER] [UPPER] [UPPER] [TM_NO] [CLASS]` | 27 | A54-006 PAKLAND PUBLIC SCHOOL 872936 C41; A54-001 BM SWEET SUPARI 773953 C30 | TM No detected but Case # is missing — prepend the Case # (e.g. A001-001) before the case name. |
| 4 | `[CASE_NO] [UPPER] [CLASS]` | 22 | A003-029 ASAR C32; A003-024 HEMERSIN C30 | Folder is missing: TM No (6 digits). |
| 5 | `[CASE_NO] [UPPER] [UPPER] [CLASS]` | 22 | A003-006 KHAN SALANTY C30; A039-015 HAK COSMETICS C3 | Folder is missing: TM No (6 digits). |
| 6 | `[CASE_NO] [UPPER] [UPPER]` | 13 | A003-028 BEHTREEN TEA; A003-055 FANTASTIC CP | Only Case # found — add 6-digit TM No and class code (e.g. C01) to the folder name so all fields can be extracted. |
| 7 | `[CASE_NO] [UPPER] [UPPER] [UPPER]` | 11 | A003-001 MULTIPAL REPLY MIX; A039-003 AMJAD ALI FBR | Only Case # found — add 6-digit TM No and class code (e.g. C01) to the folder name so all fields can be extracted. |
| 8 | `[CASE_NO] [UPPER] [UPPER] [UPPER] [UPPER]` | 10 | A003-049 TARIQ BANNU BEEF PULAO; A023-053 MINAL MALIK KHURAM ADV | Only Case # found — add 6-digit TM No and class code (e.g. C01) to the folder name so all fields can be extracted. |
| 9 | `[OTHER] [UPPER] [UPPER] [UPPER] [UPPER] [TM_NO] [CLASS]` | 10 | A54-003 CITY EDUCATION SCHOOL SYSTEM 869619 C41; A54-002 LAHORI GOLD SWEET SUPARI 773616 C30 | TM No detected but Case # is missing — prepend the Case # (e.g. A001-001) before the case name. |
| 10 | `[OTHER] [UPPER] [UPPER] [UPPER]` | 9 | A51-016 M TAHIR NTN; A51-015 IMRAN KHAN NTN | All-caps text with no structured codes — add Case # (e.g. A001-001), TM No (6 digits), and Class (e.g. C01). |

---

 to identify
Case Numbers. This requires **exactly 3 digits** before the dash (e.g. `A001-001`).
However, the real Brandex dataset contains folders with **2-digit** prefixes such as
`A52-029`, `A54-005`, `A51-016`. These are valid Case Numbers but the regex does not
match them — they fall through as `[OTHER]` tokens and the Case # field is left blank.

**Impact:** 173 case folders have a valid TM No but an empty Case # specifically because
of this mismatch. They appear in `validation_failures.csv` with `issues = "missing Case #"`.
Patterns 1, 2, 3, and 9 in the top-10 table above are all instances of this single bug.

**Affected regex (main.py line ~39):**
```python
if re.match(r'^[A-Z]\d{3}-\d{3}

| File | Contents |
|---|---|
| `validation_report.html` | Human-readable colour-coded summary |
| `validation_report.md` | This file — statistics + recommendations |
| `validation_warnings.csv` | All partial-parse warnings (one row per case) |
| `validation_failures.csv` | All complete-parse failures (one row per case) |

---

_Generated by `validate_drive.py` — no project code was modified._, part):   # ← only 3-digit prefix matched
```

**Correct regex (not applied — documented only):**
```python
if re.match(r'^[A-Z]\d{2,3}-\d{3}

| File | Contents |
|---|---|
| `validation_report.html` | Human-readable colour-coded summary |
| `validation_report.md` | This file — statistics + recommendations |
| `validation_warnings.csv` | All partial-parse warnings (one row per case) |
| `validation_failures.csv` | All complete-parse failures (one row per case) |

---

_Generated by `validate_drive.py` — no project code was modified._, part):  # ← matches A52-029 AND A001-001
```

**Note:** `main.py` was NOT modified. This fix should be applied deliberately after review,
with a comparison run using `compare_outputs.py` to confirm record counts increase.

---

## Recommendations

- **[BUG FIX REQUIRED] 173 case folders have a 2-digit Case # (e.g. `A52-029`) that the parser silently ignores.**
  Change `\d{3}` to `\d{2,3}` in the Case # regex in `parse_case_folder()`. Run a comparison
  report before and after to confirm the improvement.
- **367 case folders could not be parsed in total.** After the bug fix above, this number
  should drop significantly (to ~194). Remaining failures are genuine data-quality issues.
- **194 cases are missing TM Numbers.** The parser expects exactly 6 consecutive digits.
  5-digit or 7-digit values are not captured.
- **125 cases have no Class code.** Class codes must follow `C` + digits (e.g. `C01`, `C29`).
  Variants like `C-42`, `CL01`, or `Class01` are not matched.
- **26 duplicate composite keys detected.** Two folders producing the same
  (CLIENT NUMBER, CASE #, TM NO, CLASS) are merged into one record silently.
- **32 case folders contain no files.** They produce no pattern tick-marks.

---

## Output Files

| File | Contents |
|---|---|
| `validation_report.html` | Human-readable colour-coded summary |
| `validation_report.md` | This file — statistics + recommendations |
| `validation_warnings.csv` | All partial-parse warnings (one row per case) |
| `validation_failures.csv` | All complete-parse failures (one row per case) |

---

_Generated by `validate_drive.py` — no project code was modified._