"""
inventory.py — Sprint 4 online Google Drive inventory extractor.

Replaces the local-mount dependency entirely:

    OLD: Google Drive -> Desktop Sync -> Local Path -> Python
    NEW: Google Drive API -> Folder ID -> Python -> Results

Scans the live Brandex Drive via `drive_api` (Service Account auth, no
Drive Desktop / mounted folder required), extracts full metadata for every
client folder, case folder, and file (metadata only — file *contents* are
never read), and exports:

    export/clients.csv
    export/cases.csv
    export/files.csv
    export/drive_inventory.xlsx     (Clients / Cases / Files worksheets)
    export/inventory_report.md      (descriptive statistics only — no fixes)

Folder-name parsing (client number/name, case number/name, TM No, class
code) uses Parser V2 (`parser_v2/`) exclusively — see PROJECT_BIBLE.md §2 for
why V1 (`main.py`) is not used here. `inventory.py` never imports
`googleapiclient`/`google.oauth2` directly; all Drive API access goes
through `drive_api` (Sprint 4 Part 6 — parser/report code must not know
whether records came from the live API or a local mirror).

Usage
-----
    # Online (live Drive), using settings.json for folder IDs:
    python inventory.py --source drive

    # Online, overriding folder IDs for this run:
    python inventory.py --source drive --clients-id FOLDER_ID --consultants-id FOLDER_ID

    # Offline smoke test against sample_drive/ (no credentials needed):
    python inventory.py --source local --local-path sample_drive

    # Cap records while testing:
    python inventory.py --source drive --max 25
"""

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import List, Optional

import pandas as pd

from drive_api import load_settings, build_drive_service, walk_drive_tree, walk_local_tree
from parser_v2 import parse_client_folder, parse_case_folder, extract_full_case_name
from parser_v2.rules import classify_case_severity

BASE_DIR = Path(__file__).parent.resolve()
EXPORT_DIR = BASE_DIR / "export"
EXPORT_DIR.mkdir(exist_ok=True)


def detect_case_type(case_folder_name: str, tm_no: str) -> str:
    """Best-effort case-type classification from the folder name alone.

    Descriptive only (Sprint 4 Part 5 report is explicitly "descriptive,
    do not attempt to fix data") — not a business rule, just a label to help
    humans skim the inventory.
    """
    name_upper = case_folder_name.upper()
    if "NTN" in name_upper:
        return "NTN / Administrative"
    if " VS " in f" {name_upper} " or " V " in f" {name_upper} ":
        return "Dispute / Rectification"
    if not tm_no:
        return "Pending / No TM No"
    return "Standard"


def build_records(rows, prefix_to_remove: str = ""):
    """Consume `(client_folder, case_folder, files)` tuples (from either
    drive_api.walk_drive_tree or drive_api.walk_local_tree — identical
    shape) and build the three flat record lists Sprint 4 asks for.
    """
    clients_seen = {}
    case_records: List[dict] = []
    file_records: List[dict] = []

    for client_folder, case_folder, files in rows:
        if client_folder.id not in clients_seen:
            client_number, client_name = parse_client_folder(client_folder.name)
            clients_seen[client_folder.id] = {
                "FOLDER ID": client_folder.id,
                "FOLDER NAME": client_folder.name,
                "PARENT FOLDER": client_folder.parent_id,
                "CLIENT CODE": client_number,
                "CLIENT NAME": client_name,
                "CREATED": client_folder.created_time,
                "MODIFIED": client_folder.modified_time,
            }

        # A client with zero case folders is yielded once as
        # (client_folder, None, []) so it still appears in clients.csv/totals
        # (Sprint 4 Part 2: every client folder must be extracted) without
        # fabricating a case record for it.
        if case_folder is None:
            continue

        case_no, case_name, tm_no, class_code = parse_case_folder(case_folder.name)
        full_name = extract_full_case_name(case_folder.name, tm_no)
        if full_name:
            case_name = full_name
        severity = classify_case_severity(case_no, tm_no, class_code)

        case_records.append({
            "FOLDER ID": case_folder.id,
            "PARENT CLIENT": client_folder.id,
            "CLIENT CODE": clients_seen[client_folder.id]["CLIENT CODE"],
            "CASE FOLDER NAME": case_folder.name,
            "CASE #": case_no,
            "CASE NAME": case_name,
            "TM NO": tm_no,
            "CLASS": class_code,
            "CASE TYPE": detect_case_type(case_folder.name, tm_no),
            "FILE COUNT": len(files),
            "CREATED": case_folder.created_time,
            "MODIFIED": case_folder.modified_time,
            "MISSING CASE #": severity.is_failure,
            "MISSING TM/CLASS": severity.is_warning,
        })

        for f in files:
            file_records.append({
                "FILE ID": f.id,
                "FILE NAME": f.name,
                "EXTENSION": f.extension,
                "MIME TYPE": f.mime_type,
                "SIZE (BYTES)": f.size,
                "CREATED": f.created_time,
                "MODIFIED": f.modified_time,
                "PARENT CASE FOLDER": case_folder.id,
                "DRIVE URL": f.url,
            })

    client_records = list(clients_seen.values())
    return client_records, case_records, file_records


def write_report(client_records, case_records, file_records, out_path: Path):
    total_clients = len(client_records)
    total_cases = len(case_records)
    total_files = len(file_records)

    case_types = Counter(c["CASE TYPE"] for c in case_records)
    missing_tm = sum(1 for c in case_records if not c["TM NO"])
    missing_class = sum(1 for c in case_records if not c["CLASS"])
    empty_cases = sum(1 for c in case_records if c["FILE COUNT"] == 0)

    tm_counter = Counter(c["TM NO"] for c in case_records if c["TM NO"])
    duplicate_tms = {tm: n for tm, n in tm_counter.items() if n > 1}

    if case_records:
        largest = max(case_records, key=lambda c: c["FILE COUNT"])
        avg_files = total_files / total_cases if total_cases else 0
    else:
        largest = None
        avg_files = 0

    lines = [
        "# Drive Inventory Report",
        "",
        "Descriptive only — no data was modified or auto-corrected.",
        "",
        "## Totals",
        "",
        f"- Total Clients: **{total_clients}**",
        f"- Total Cases: **{total_cases}**",
        f"- Total Files: **{total_files}**",
        "",
        "## Case Types",
        "",
    ]
    for case_type, count in case_types.most_common():
        lines.append(f"- {case_type}: {count}")

    lines += [
        "",
        "## Data Quality (descriptive)",
        "",
        f"- Missing TM Numbers: {missing_tm} ({missing_tm / total_cases:.1%} of cases)" if total_cases else "- Missing TM Numbers: 0",
        f"- Missing Class codes: {missing_class} ({missing_class / total_cases:.1%} of cases)" if total_cases else "- Missing Class codes: 0",
        f"- Empty case folders (0 files): {empty_cases}",
        f"- Duplicate TM Numbers: {len(duplicate_tms)}",
    ]
    if duplicate_tms:
        for tm, n in sorted(duplicate_tms.items(), key=lambda x: -x[1])[:20]:
            lines.append(f"  - `{tm}` appears in {n} case folders")

    lines += [
        "",
        "## Size",
        "",
        f"- Largest case folder (by file count): "
        + (f"`{largest['CASE FOLDER NAME']}` — {largest['FILE COUNT']} files" if largest else "n/a"),
        f"- Average files per case: {avg_files:.2f}",
        "",
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")


def run(source: str, clients_id: Optional[str], consultants_id: Optional[str],
        local_path: Optional[str], max_clients: Optional[int], workers: int):
    all_rows = []

    if source == "drive":
        settings = load_settings()
        clients_id = clients_id or settings.clients_folder_id
        consultants_id = consultants_id or settings.consultants_folder_id
        if not clients_id and not consultants_id:
            print("❌ No folder IDs provided. Pass --clients-id/--consultants-id or "
                  "set clients_folder_id/consultants_folder_id in settings.json.")
            sys.exit(1)

        # Passing the credentials *path* (not a pre-built service) lets
        # walk_drive_tree fan out real work across worker threads, each with
        # its own Drive service instance (googleapiclient connections are not
        # thread-safe — see drive_api/scanner.py). Fail fast here if the key
        # is missing/invalid rather than deep inside the thread pool.
        build_drive_service(settings.credentials_path)
        if clients_id:
            print(f"Scanning clients root {clients_id} ...")
            all_rows.extend(walk_drive_tree(settings.credentials_path, clients_id, workers=workers, max_clients=max_clients))
        if consultants_id:
            print(f"Scanning consultants root {consultants_id} ...")
            all_rows.extend(walk_drive_tree(settings.credentials_path, consultants_id, workers=workers, max_clients=max_clients))
    else:
        if not local_path:
            print("❌ --local-path is required when --source local")
            sys.exit(1)
        print(f"Scanning local path {local_path} ...")
        all_rows.extend(walk_local_tree(local_path, max_clients=max_clients))

    print(f"Found {len(all_rows)} case folders. Building records ...")
    client_records, case_records, file_records = build_records(all_rows)

    clients_df = pd.DataFrame(client_records)
    cases_df = pd.DataFrame(case_records)
    files_df = pd.DataFrame(file_records)

    clients_df.to_csv(EXPORT_DIR / "clients.csv", index=False)
    cases_df.to_csv(EXPORT_DIR / "cases.csv", index=False)
    files_df.to_csv(EXPORT_DIR / "files.csv", index=False)

    with pd.ExcelWriter(EXPORT_DIR / "drive_inventory.xlsx", engine="openpyxl") as writer:
        clients_df.to_excel(writer, sheet_name="Clients", index=False)
        cases_df.to_excel(writer, sheet_name="Cases", index=False)
        files_df.to_excel(writer, sheet_name="Files", index=False)

    write_report(client_records, case_records, file_records, EXPORT_DIR / "inventory_report.md")

    print(f"✅ Done. {len(client_records)} clients, {len(case_records)} cases, {len(file_records)} files.")
    print(f"   export/clients.csv, export/cases.csv, export/files.csv")
    print(f"   export/drive_inventory.xlsx")
    print(f"   export/inventory_report.md")


def main():
    parser = argparse.ArgumentParser(description="Sprint 4 online Drive inventory extractor")
    parser.add_argument("--source", choices=["drive", "local"], default="drive")
    parser.add_argument("--clients-id", help="Drive folder ID for '1 ALL CLIENTS' (overrides settings.json)")
    parser.add_argument("--consultants-id", help="Drive folder ID for '2 CONSULTANTS' (overrides settings.json)")
    parser.add_argument("--local-path", help="Local directory to scan when --source local (e.g. sample_drive)")
    parser.add_argument("--max", type=int, default=None, help="Cap number of client folders processed per root")
    parser.add_argument("--workers", type=int, default=8, help="Thread pool size for live Drive scanning")
    args = parser.parse_args()

    run(args.source, args.clients_id, args.consultants_id, args.local_path, args.max, args.workers)


if __name__ == "__main__":
    main()
