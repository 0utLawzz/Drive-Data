# Drive Folders List

A Python CLI tool for trademark law firms. Scans Google Drive–mirrored folder structures, extracts structured case data from folder names, and exports to Google Sheets or local Excel/CSV files.

## How to run

### Interactive CLI (original tool)
Start the **Run** workflow or run `python main.py` in the shell.

The menu requires:
- **Option 4 – Custom Path** to point at any folder on Replit (the defaults `F:\Brandex004\...` are Windows paths).
- `credentials.json` in the project root if you want Google Sheets upload (see *First-time setup* below).

### Non-interactive batch export (for testing / comparison)
```bash
python batch_export.py <drive_path> <output_prefix> [--max N]

# Examples:
python batch_export.py sample_drive old_output       # scan sample_drive/, write export/old_output.{csv,xlsx}
python batch_export.py sample_drive new_output       # run again after refactoring main.py logic
```

### Compare old vs new output
```bash
python compare_outputs.py export/old_output.csv export/new_output.csv
# Produces:
#   export/comparison_report.csv   — machine-readable diff
#   export/comparison_report.html  — colour-coded HTML report
```

### Workflow for refactoring validation
1. `python batch_export.py sample_drive old_output`  — capture baseline from current `main.py` logic
2. Make your changes to `main.py` (or copy refactored logic into `batch_export.py`)
3. `python batch_export.py sample_drive new_output`  — capture output from new logic
4. `python compare_outputs.py export/old_output.csv export/new_output.csv`  — generate diff report

## First-time setup (Google Sheets)
1. Place your Google Service Account key as `credentials.json` in the project root (gitignored — never commit).
2. The Sheet ID is hardcoded in `main.py` (`SHEET_ID`). Update it to your own sheet.

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Data | pandas, openpyxl |
| Google integration | gspread, google-auth |
| Pattern matching | re (regex) |

## Key files

| File | Purpose |
|---|---|
| `main.py` | Original interactive CLI — parsing, pattern matching, Google Sheets auth, export |
| `batch_export.py` | Non-interactive runner for testing and comparison workflows |
| `compare_outputs.py` | Diffs two CSV/Excel outputs; produces CSV + HTML comparison report |
| `sample_drive/` | Realistic sample folder structure (7 clients, 15 cases) for local testing |
| `requirements.txt` | Python dependencies |
| `credentials.json` | Google Service Account key — place here, **never commit** |
| `export/` | Auto-created output directory for Excel/CSV/report files |

## User preferences

- Refactor to "Data-Shaper V2" is planned as a follow-up task.
