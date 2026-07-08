"""
scanner/exporter.py — Export layer for Data-Shaper V2.

Handles:
  • Local Excel (.xlsx) export
  • Local CSV (.csv) export
  • Google Sheets upload via service account
"""

import os
from pathlib import Path

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

from utils.helpers import load_settings
from utils.logger import logger

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE_DIR  = Path(__file__).parent.parent
_CREDS_PATH = _BASE_DIR / "credentials.json"
_EXPORT_DIR = _BASE_DIR / "export"

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Output column order — must match Google Sheets header order exactly
EXPORT_COLUMNS = [
    "CLIENT NUMBER", "CLIENT NAME", "CASE #", "CASE NAME", "TM NO", "CLASS",
    "FILES", "EXT",
    "TM-1", "TM-48", "EXAM", "ACK", "ACCEPTANCE", "D-NOTE",
    "TM-16", "TM-50", "TM-06", "COMPANY", "OPPO", "PUB", "CERTIFICATE",
    "DATE ADDED",
]

# Short names for export files
_SHORT_NAMES = {
    "consultants_data": "cons_patterns",
    "clients_data":     "clients_patterns",
    "all_data":         "all_patterns",
    "custom_data":      "custom_patterns",
}

# Google Sheets column headers (with emoji decorations)
_SHEET_HEADERS = [
    "📋 CLIENT NUMBER", "👤 CLIENT NAME", "📁 CASE #", "📝 CASE NAME",
    "🔢 TM NO", "📚 CLASS", "📎 FILES", "📄 EXT",
    "📄 TM-1", "📄 TM-48", "📝 EXAM", "✅ ACK", "✅ ACCEPTANCE",
    "📋 D-NOTE", "📄 TM-16", "📄 TM-50", "📄 TM-06",
    "🏢 COMPANY", "❌ OPPO", "📰 PUB", "📜 CERTIFICATE", "📅 DATE ADDED",
]


# ---------------------------------------------------------------------------
# Local export
# ---------------------------------------------------------------------------

def export_local(records: list[dict], filename_prefix: str) -> None:
    """Export *records* to local .xlsx and .csv files inside the export/ dir."""
    if not records:
        logger.info("No records to export locally.")
        return

    settings = load_settings()
    os.makedirs(_EXPORT_DIR, exist_ok=True)

    df = pd.DataFrame(records)

    # Only keep known columns that actually exist in the dataframe
    cols = [c for c in EXPORT_COLUMNS if c in df.columns]
    df = df[cols]

    short_name = _SHORT_NAMES.get(filename_prefix, filename_prefix)

    if settings.get("excel_export", True):
        excel_path = _EXPORT_DIR / f"{short_name}.xlsx"
        df.to_excel(excel_path, index=False, engine="openpyxl")
        logger.info("📊 Excel: %s", excel_path)

    if settings.get("csv_export", True):
        csv_path = _EXPORT_DIR / f"{short_name}.csv"
        df.to_csv(csv_path, index=False)
        logger.info("📄 CSV:   %s", csv_path)

    logger.info("💾 Exported %d records locally.", len(df))


def quick_export_local(records: list[dict], filename: str = "drive_data_export") -> None:
    """
    Quick export — no pattern columns, minimal column set.
    Used by menu option 5 (Quick Export, No Patterns).
    """
    if not records:
        logger.info("No records to export.")
        return

    os.makedirs(_EXPORT_DIR, exist_ok=True)

    quick_cols = ["CLIENT NUMBER", "CLIENT NAME", "CASE #", "CASE NAME",
                  "TM NO", "CLASS", "FILES", "EXT", "DATE ADDED"]

    df = pd.DataFrame(records)
    cols = [c for c in quick_cols if c in df.columns]
    df = df[cols]

    excel_path = _EXPORT_DIR / f"{filename}.xlsx"
    df.to_excel(excel_path, index=False, engine="openpyxl")
    logger.info("Exported %d records to %s", len(df), excel_path)

    csv_path = _EXPORT_DIR / f"{filename}.csv"
    df.to_csv(csv_path, index=False)
    logger.info("Also exported to %s", csv_path)


# ---------------------------------------------------------------------------
# Google Sheets
# ---------------------------------------------------------------------------

def get_google_sheets_client() -> gspread.Client | None:
    """Initialise and return a gspread client using credentials.json."""
    if not _CREDS_PATH.exists():
        logger.error("❌ credentials.json not found at: %s", _CREDS_PATH)
        return None
    try:
        creds = Credentials.from_service_account_file(str(_CREDS_PATH), scopes=_SCOPES)
        return gspread.authorize(creds)
    except Exception as exc:
        logger.error("Error connecting to Google Sheets: %s", exc)
        return None


def _setup_sheet_headers(spreadsheet: gspread.Spreadsheet, sheet_name: str) -> gspread.Worksheet | None:
    """Ensure the target worksheet exists and has the correct headers."""
    try:
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="22")
            logger.info("✅ Created new worksheet: %s", sheet_name)

        worksheet.update(values=[_SHEET_HEADERS], range_name="A1:V1")
        return worksheet
    except Exception as exc:
        logger.error("Error setting up sheet headers: %s", exc)
        return None


def upload_to_sheets(records: list[dict], sheet_id: str = "", sheet_name: str = "") -> bool:
    """Upload *records* to the configured Google Sheet."""
    settings = load_settings()
    sheet_id   = sheet_id   or settings.get("sheet_id", "")
    sheet_name = sheet_name or settings.get("sheet_name", "List")

    if not settings.get("google_sheet", True):
        logger.info("Google Sheets upload is disabled in settings.json.")
        return False

    if not sheet_id:
        logger.error("❌ sheet_id is not configured in config/settings.json.")
        return False

    client = get_google_sheets_client()
    if not client:
        return False

    try:
        spreadsheet = client.open_by_key(sheet_id)
        worksheet   = _setup_sheet_headers(spreadsheet, sheet_name)
        if not worksheet:
            return False

        if not records:
            logger.info("✅ No records to upload.")
            return True

        # Build rows in column order
        data = []
        for rec in records:
            row = [rec.get(col, "") for col in EXPORT_COLUMNS]
            data.append(row)

        worksheet.append_rows(data)
        logger.info("✅ Uploaded %d records to Google Sheets.", len(records))
        return True

    except Exception as exc:
        logger.error("Error uploading to Google Sheets: %s", exc)
        return False
