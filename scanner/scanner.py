"""
scanner/scanner.py — Directory traversal for Data-Shaper V2.

scan_directory()   — pure traversal, no parsing, no regex.
process_directory() — full pipeline: scan → parse → detect → group → records.
"""

import os
from datetime import datetime
from pathlib import Path

from scanner.parser import parse_client_folder, parse_case_folder, validate_client_folder
from scanner.detector import check_file_patterns
from utils.helpers import sanitize_record
from utils.logger import logger

# Files to silently ignore during traversal
_SKIP_FILES = {"desktop.ini"}
_SKIP_EXTENSIONS = {".ini"}


# ---------------------------------------------------------------------------
# Pure traversal — no parsing, no regex
# ---------------------------------------------------------------------------

def scan_directory(base_path: str, max_records: int | None = None) -> list[dict]:
    """
    Walk *base_path* two levels deep (client → case) and collect raw entries.

    Each entry is a plain dict::

        {
            "client_folder": str,   # raw folder name
            "case_folder":   str,   # raw sub-folder name
            "files":         list[str],  # filenames inside the case folder
        }

    No parsing or regex happens here.
    """
    entries: list[dict] = []
    count = 0

    if not os.path.isdir(base_path):
        logger.warning("scan_directory: path does not exist — %s", base_path)
        return entries

    for client_folder in sorted(os.listdir(base_path)):
        client_path = os.path.join(base_path, client_folder)
        if not os.path.isdir(client_path):
            continue

        for case_folder in sorted(os.listdir(client_path)):
            if max_records is not None and count >= max_records:
                return entries

            case_path = os.path.join(client_path, case_folder)
            if not os.path.isdir(case_path):
                continue

            # Collect filenames, skipping system/hidden files
            files: list[str] = []
            for fname in os.listdir(case_path):
                if fname.lower() in _SKIP_FILES:
                    continue
                ext = Path(fname).suffix.lower()
                if ext in _SKIP_EXTENSIONS:
                    continue
                if os.path.isfile(os.path.join(case_path, fname)):
                    files.append(fname)

            # Always append the entry even if the case folder has no files —
            # this preserves the original behaviour where empty case folders
            # still produced a record (with blank FILES/EXT columns).
            entries.append({
                "client_folder": client_folder,
                "case_folder": case_folder,
                "files": files,
            })
            count += 1

    return entries


# ---------------------------------------------------------------------------
# Full pipeline: scan → parse → detect → group (duplicate prevention) → records
# ---------------------------------------------------------------------------

def process_directory(
    base_path: str,
    prefix_to_remove: str = "",   # kept for backward-compat, not used
    max_records: int | None = None,
) -> list[dict]:
    """
    Scan *base_path* and return a list of structured records ready for export.

    Steps
    -----
    1. scan_directory  — traverse, collect raw folder/file names
    2. parse           — extract structured fields from folder names
    3. validate        — log warnings for non-conforming client folders
    4. detect          — check file names against document patterns
    5. group           — merge sub-folders of the same case (duplicate prevention)
    6. build records   — assemble final output dicts
    """
    start = datetime.now()
    logger.info("=" * 60)
    logger.info("Scan started: %s", base_path)
    logger.info("=" * 60)

    raw_entries = scan_directory(base_path, max_records)
    logger.info("Folders discovered: %d", len(raw_entries))

    # Group by case key to prevent duplicate records
    case_groups: dict[tuple, list[str]] = {}
    warn_count = 0

    for entry in raw_entries:
        # --- Parse client folder ---
        validation = validate_client_folder(entry["client_folder"])
        for w in validation["warnings"]:
            logger.warning(w)
            warn_count += 1

        client_number = validation["client_number"]
        client_name = validation["client_name"]

        # --- Parse case folder ---
        case_no, case_name, tm_no, class_code = parse_case_folder(entry["case_folder"])

        if not case_no:
            logger.warning("Could not extract case number from: '%s'", entry["case_folder"])
            warn_count += 1

        # --- Build grouping key ---
        case_key = (client_number, client_name, case_no, case_name, tm_no, class_code)

        # --- Collect file stems + extensions ---
        for fname in entry["files"]:
            stem, ext = os.path.splitext(fname)
            packed = f"{stem}|{ext.lstrip('.')}"
            if case_key not in case_groups:
                case_groups[case_key] = []
            case_groups[case_key].append(packed)

    # --- Build final records ---
    records: list[dict] = []
    for (client_number, client_name, case_no, case_name, tm_no, class_code), files in case_groups.items():
        file_names = "\n".join(f.split("|")[0] for f in files if f.split("|")[0])
        file_exts  = "\n".join(f.split("|")[1] for f in files if f.split("|")[1])

        pattern_results = check_file_patterns(file_names)

        record = {
            "CLIENT NUMBER": client_number,
            "CLIENT NAME":   client_name,
            "CASE #":        case_no,
            "CASE NAME":     case_name,
            "TM NO":         tm_no,
            "CLASS":         class_code,
            "FILES":         file_names,
            "EXT":           file_exts,
            "DATE ADDED":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        record.update(pattern_results)

        # Sanitise against spreadsheet formula injection
        records.append(sanitize_record(record))

    duration = (datetime.now() - start).total_seconds()
    logger.info("Records built: %d | Warnings: %d | Duration: %.2fs", len(records), warn_count, duration)

    return records
