# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-07-09

### Added
- `validate_drive.py` — real-world validation tool that connects to Google Drive via
  the Drive API (v3) and traverses the live Brandex folder hierarchy without modifying
  any project code.  Collects 14 data-quality metrics per run:
  total client/case/file counts, records generated, parse failures, parse warnings,
  unrecognized client folders, duplicate composite keys, empty case folders, missing
  TM numbers, missing Class codes, missing Case numbers, fully-parsed case count,
  and processing duration.
- `validate_drive.py` generates four output artefacts in `export/`:
  `validation_report.html`, `validation_report.md`, `validation_warnings.csv`,
  `validation_failures.csv`.
- Top-10 unrecognised folder-naming pattern analysis with structural token signatures
  (e.g. `[CASE_NO] [WORDS]`) and per-pattern parser improvement suggestions.
- `batch_export.py` — non-interactive runner that imports parsing logic directly from
  `main.py` so any future refactor is automatically reflected in test exports.
- `compare_outputs.py` — diffs two CSV/Excel exports and produces a colour-coded HTML
  diff report with added / removed / changed record categories; duplicate composite
  keys in either file are warned rather than silently dropped; all user-derived values
  are HTML-escaped before output.
- `sample_drive/` — 7 synthetic client folders, 15 case folders with realistic
  trademark document file names for local offline testing.
- `google-api-python-client` added to runtime dependencies for Drive API v3 access.

### Task context
Real-world validation was requested to verify parser behaviour against the live
Brandex Google Drive dataset (not sample data).  No changes were made to `main.py`
or any parsing logic; confirmed issues are documented in the generated reports only.

Host: Replit
Timestamp: 2026-07-09

---

## [1.0.0] - 2026-06-06

### Added
- Recursive directory traversal using `os.walk`.
- 13-category regex pattern matching engine for trademark documents.
- Google Sheets upload with gspread and service account authentication.
- Duplicate detection and prevention before each upload.
- Local Excel and CSV export via pandas and openpyxl.
- Interactive CLI menu for directory and output mode selection.

### Changed
- Standardized documentation format.

Host: LAPTOP-0UTLAWZZ
Timestamp: 2026-06-06 03:19:00 +05:00

---

## 👨‍💻 Credits

**By OutLawZ™**

Website: https://www.brandex.pk

Contact:

📧 Email: net2tara@gmail.com
🌐 Website: https://www.brandex.pk

---
Made with ❤️ by OutLawZ™
