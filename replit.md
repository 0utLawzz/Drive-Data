# Drive Folders List

A Python CLI tool for trademark law firms. Scans Google Drive–mirrored folder structures, extracts structured case data from folder names, and exports to Google Sheets or local Excel/CSV files.

## How to run

The app runs as an interactive CLI. Start the **Run** workflow (or `python main.py` in the shell).

### First-time setup
1. Place your Google Service Account key file as `credentials.json` in the project root (never commit this file — it is gitignored).
2. The hardcoded folder paths (`F:\Brandex004\My Drive\...`) are Windows-specific. Use **Option 4 – Custom Path** in the menu to point the tool at any folder on Replit, or update `consultants_path` / `clients_path` in `main.py`.

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
| `main.py` | Full CLI logic: parsing, pattern matching, Google Sheets auth, export |
| `requirements.txt` | Python dependencies |
| `credentials.json` | Google Service Account key — place here, **never commit** |
| `export/` | Auto-created output directory for Excel/CSV files |

## User preferences

- Refactor to "Data-Shaper V2" is planned as a follow-up task.
