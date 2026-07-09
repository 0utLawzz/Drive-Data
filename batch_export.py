"""
batch_export.py — Non-interactive runner for Drive Folders List.

Imports the core processing logic directly from main.py, so any changes
made during refactoring are automatically picked up on the next run.

Typical comparison workflow
---------------------------
Step 1 — Capture baseline BEFORE touching main.py:
    python batch_export.py sample_drive old_output

Step 2 — Refactor / fix bugs in main.py (or batch_export's imports).

Step 3 — Capture new output:
    python batch_export.py sample_drive new_output

Step 4 — Generate diff report:
    python compare_outputs.py export/old_output.csv export/new_output.csv

Usage
-----
    python batch_export.py <drive_path> <output_prefix> [--max N]

Examples:
    python batch_export.py sample_drive old_output
    python batch_export.py sample_drive new_output --max 50
"""

import sys
import argparse
import os
from pathlib import Path
from datetime import datetime
import pandas as pd

# ---------------------------------------------------------------------------
# Import core logic from main.py so this runner always reflects the current
# state of main.py without duplicating any business logic.
# ---------------------------------------------------------------------------
# We import only the functions we need; main() itself is never called.
try:
    from main import process_directory
except ImportError as exc:
    print(f"❌ Could not import from main.py: {exc}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
BASE_DIR  = Path(__file__).parent.resolve()
EXPORT_DIR = str(BASE_DIR / "export")
os.makedirs(EXPORT_DIR, exist_ok=True)

COLUMNS = [
    "CLIENT NUMBER", "CLIENT NAME", "CASE #", "CASE NAME", "TM NO", "CLASS",
    "FILES", "EXT", "TM-1", "TM-48", "EXAM", "ACK", "ACCEPTANCE", "D-NOTE",
    "TM-16", "TM-50", "TM-06", "COMPANY", "OPPO", "PUB", "CERTIFICATE", "DATE ADDED"
]


def export(records, output_prefix):
    if not records:
        print("⚠️  No records found — nothing to export.")
        return

    df = pd.DataFrame(records)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNS]

    excel_path = os.path.join(EXPORT_DIR, f"{output_prefix}.xlsx")
    csv_path   = os.path.join(EXPORT_DIR, f"{output_prefix}.csv")

    df.to_excel(excel_path, index=False, engine="openpyxl")
    df.to_csv(csv_path, index=False)

    print(f"✅ Exported {len(df)} records:")
    print(f"   📊 Excel : {excel_path}")
    print(f"   📄 CSV   : {csv_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Non-interactive Drive Folders List exporter (imports from main.py)"
    )
    parser.add_argument("drive_path",    help="Root folder to scan (e.g. sample_drive)")
    parser.add_argument("output_prefix", help="Output file name without extension (saved to export/)")
    parser.add_argument(
        "--max", type=int, default=None, metavar="N",
        help="Cap the number of records processed (useful for quick tests)"
    )
    args = parser.parse_args()

    drive_path = Path(args.drive_path)
    if not drive_path.exists():
        print(f"❌ Path not found: {drive_path}")
        sys.exit(1)

    print(f"📁 Scanning  : {drive_path.resolve()}")
    print(f"   Output    : export/{args.output_prefix}.{{csv,xlsx}}")

    # process_directory signature: (base_path, prefix_to_remove, max_records)
    # prefix_to_remove is only used for display purposes in some versions;
    # we pass an empty string to stay compatible with the current main.py.
    records = process_directory(str(drive_path), "", args.max)
    print(f"   Found {len(records)} records")

    export(records, args.output_prefix)


if __name__ == "__main__":
    main()
