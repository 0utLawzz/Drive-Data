"""
Shared utility helpers for Data-Shaper V2.
"""

import json
import os
from pathlib import Path

# Characters that spreadsheet apps interpret as formula prefixes
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

_BASE_DIR = Path(__file__).parent.parent
_CONFIG_DIR = _BASE_DIR / "config"


# ---------------------------------------------------------------------------
# Spreadsheet injection sanitiser
# ---------------------------------------------------------------------------

def sanitize_cell(value: str) -> str:
    """
    Prevent CSV / Excel / Google Sheets formula injection.

    Any cell value starting with a formula prefix character is prefixed with
    a single quote so it is treated as plain text by spreadsheet apps.
    """
    if value and isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def sanitize_record(record: dict) -> dict:
    """Return a copy of *record* with all string values sanitised."""
    return {k: sanitize_cell(str(v)) if isinstance(v, str) else v
            for k, v in record.items()}


# ---------------------------------------------------------------------------
# Config loaders
# ---------------------------------------------------------------------------

def load_settings() -> dict:
    """Load config/settings.json. Returns defaults if file is missing."""
    path = _CONFIG_DIR / "settings.json"
    defaults = {
        "google_sheet": True,
        "excel_export": True,
        "csv_export": True,
        "submission_module": False,
        "debug": False,
        "sheet_id": "",
        "sheet_name": "List",
        "consultants_path": "",
        "clients_path": "",
    }
    if not path.exists():
        return defaults
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {**defaults, **data}


def load_patterns() -> dict:
    """Load config/patterns.json. Returns empty dict if file is missing."""
    path = _CONFIG_DIR / "patterns.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)
