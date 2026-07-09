"""
validate_drive.py — Real-world validation of the Drive Folders List parser
against the actual Brandex Google Drive dataset.

Connects to Google Drive via credentials.json, traverses the same
client/case/file hierarchy that main.py processes locally, and produces:

  export/validation_report.html  — human-readable summary
  export/validation_report.md    — statistics + recommendations
  export/validation_warnings.csv — partial-parse warnings (one row per case)
  export/validation_failures.csv — complete-parse failures (one row per case)

Usage:
    python validate_drive.py
    python validate_drive.py --clients-id FOLDER_ID --consultants-id FOLDER_ID
    python validate_drive.py --clients-id FOLDER_ID   # consultants optional
    python validate_drive.py --search-name "1 ALL CLIENTS"

The script DOES NOT modify main.py or any project code.
Any confirmed bugs are documented in the reports, not silently fixed.
"""

import argparse
import csv
import html
import os
import re
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# ── Google API ────────────────────────────────────────────────────────────────
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ── Parsing logic (imported directly from main.py — unchanged) ───────────────
from main import (
    parse_client_folder,
    parse_case_folder,
    extract_full_case_name,
    check_file_patterns,
)

# ── Output dir ────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.resolve()
EXPORT_DIR = BASE_DIR / "export"
EXPORT_DIR.mkdir(exist_ok=True)

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
]

# Columns that make a record's identity key (mirrors compare_outputs.py)
KEY_COLS = ["CLIENT NUMBER", "CASE #", "TM NO", "CLASS"]

# ─────────────────────────────────────────────────────────────────────────────
# Drive API helpers
# ─────────────────────────────────────────────────────────────────────────────

def build_drive_service(creds_path: str):
    if not os.path.exists(creds_path):
        print(f"❌  credentials.json not found at: {creds_path}")
        print("    Place your Google Service Account key at that path and retry.")
        sys.exit(1)
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


# Thread-local storage: each worker thread gets its own Drive service instance
# (googleapiclient HTTP connections are not safe to share across threads).
_thread_local = threading.local()

def _get_thread_service(creds_path: str):
    """Return a Drive service local to the calling thread, creating it if needed."""
    if not hasattr(_thread_local, "service"):
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        _thread_local.service = build("drive", "v3", credentials=creds)
    return _thread_local.service


def list_items(service, parent_id: str, mime_filter: str | None = None,
               *, page_size=1000) -> list[dict]:
    """Return all non-trashed children of parent_id (files or folders)."""
    q = f"'{parent_id}' in parents and trashed = false"
    if mime_filter:
        q += f" and mimeType = '{mime_filter}'"

    items, page_token = [], None
    while True:
        try:
            resp = service.files().list(
                q=q,
                fields="nextPageToken, files(id, name, mimeType)",
                pageSize=page_size,
                pageToken=page_token,
            ).execute()
        except HttpError as exc:
            print(f"   ⚠️  Drive API error listing {parent_id}: {exc}")
            break
        items.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return items


def find_folder_by_name(service, name: str) -> str | None:
    """Search all accessible folders for a given name; return first match ID.
    Paginates fully so results are not capped at one page.
    """
    q = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    page_token = None
    while True:
        try:
            resp = service.files().list(
                q=q,
                fields="nextPageToken, files(id, name, parents)",
                pageSize=100,
                pageToken=page_token,
            ).execute()
        except HttpError as exc:
            print(f"   ⚠️  Drive API error searching for '{name!r}': {exc}")
            return None
        files = resp.get("files", [])
        if files:
            return files[0]["id"]   # return first match found
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return None


FOLDER_MIME = "application/vnd.google-apps.folder"


# ─────────────────────────────────────────────────────────────────────────────
# Parsing diagnostics
# ─────────────────────────────────────────────────────────────────────────────

CLIENT_PATTERN = re.compile(r"^[A-Z]-\d+\s+.+$")
CASE_NO_PATTERN  = re.compile(r"^[A-Z]\d{3}-\d{3}$")
TM_NO_PATTERN    = re.compile(r"^\d{6}$")
CLASS_PATTERN    = re.compile(r"^[C]\d+$")


def diagnose_client(folder_name: str) -> dict:
    """Return parse result + issues for a client folder."""
    client_number, client_name = parse_client_folder(folder_name)
    recognized = bool(CLIENT_PATTERN.match(folder_name))
    issues = []
    if not recognized:
        issues.append("does not match pattern [A-Z]-NNN ClientName")
    return {
        "folder_name": folder_name,
        "client_number": client_number,
        "client_name": client_name,
        "recognized": recognized,
        "issues": issues,
    }


def diagnose_case(folder_name: str) -> dict:
    """Return full parse result + per-field issues for a case folder."""
    case_no, case_name, tm_no, class_code = parse_case_folder(folder_name)
    full_name = extract_full_case_name(folder_name, tm_no)
    if full_name:
        case_name = full_name

    issues   = []
    warnings = []

    if not case_no:
        issues.append("missing Case # (expected pattern like A001-001)")
    if not tm_no:
        issues.append("missing TM No (expected 6-digit number)")
    if not class_code:
        warnings.append("missing Class code (expected C01, C29, etc.)")

    # Severity: failure = missing case_no OR tm_no; warning = missing class only
    is_failure = (not case_no) or (not tm_no)
    is_warning = (not is_failure) and bool(warnings)
    is_ok      = not issues and not warnings

    return {
        "folder_name": folder_name,
        "case_no":     case_no,
        "case_name":   case_name,
        "tm_no":       tm_no,
        "class_code":  class_code,
        "issues":      issues,
        "warnings":    warnings,
        "is_failure":  is_failure,
        "is_warning":  is_warning,
        "is_ok":       is_ok,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Pattern analysis for unparsed folder names
# ─────────────────────────────────────────────────────────────────────────────

def describe_token_pattern(folder_name: str) -> str:
    """
    Replace concrete values with type tokens to reveal structural patterns.
    e.g. "A001-001 Brand Name 123456 C01" → "[CASE_NO] [WORDS] [TM_NO] [CLASS]"
    """
    parts = folder_name.split()
    tokens = []
    for p in parts:
        if re.match(r"^[A-Z]\d{3}-\d{3}$", p):
            tokens.append("[CASE_NO]")
        elif re.match(r"^\d{6}$", p):
            tokens.append("[TM_NO]")
        elif re.match(r"^[C]\d+$", p):
            tokens.append("[CLASS]")
        elif re.match(r"^[A-Z]-\d+$", p):
            tokens.append("[CLIENT_NO]")
        elif re.match(r"^\d{4,5}$", p):
            tokens.append("[SHORT_NUM]")
        elif re.match(r"^\d+$", p):
            tokens.append("[NUM]")
        elif re.match(r"^[A-Z]+$", p):
            tokens.append("[UPPER]")
        elif re.match(r"^[A-Z][a-z]+$", p):
            tokens.append("[Word]")
        elif re.match(r"^\d{2}-\d{2}-\d{4}$", p):
            tokens.append("[DATE]")
        else:
            tokens.append("[OTHER]")
    return " ".join(tokens)


def top_n_patterns(folder_names: list[str], n: int = 10) -> list[dict]:
    """Group unparsed folder names by their structural pattern, return top N."""
    pattern_map: dict[str, list[str]] = defaultdict(list)
    for name in folder_names:
        pat = describe_token_pattern(name)
        pattern_map[pat].append(name)

    sorted_pats = sorted(pattern_map.items(), key=lambda x: -len(x[1]))[:n]
    return [
        {"pattern": pat, "count": len(examples), "examples": examples[:3]}
        for pat, examples in sorted_pats
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Main traversal
# ─────────────────────────────────────────────────────────────────────────────

class ValidationStats:
    def __init__(self):
        self.root_folders_scanned    = 0
        self.client_folders_scanned  = 0
        self.case_folders_scanned    = 0
        self.files_scanned           = 0
        self.records_generated       = 0

        self.unrecognized_clients    = []   # list of folder names
        self.failures                = []   # list of dicts (case-level)
        self.warnings                = []   # list of dicts (case-level)
        self.duplicates              = []   # list of dicts
        self.empty_cases             = []   # list of folder names
        self.missing_tm              = []   # case folder names
        self.missing_class           = []   # case folder names
        self.missing_case_no         = []   # case folder names
        self.successful_parses       = 0

        self.seen_keys               = {}   # key → first client/case path
        self.start_time              = time.time()
        self.end_time: float | None  = None

    @property
    def duration_seconds(self) -> float:
        end = self.end_time or time.time()
        return round(end - self.start_time, 2)

    def finish(self):
        self.end_time = time.time()


def _process_client_folder(cf: dict, creds_path: str) -> dict:
    """
    Worker: process one client folder and return a plain dict of results.
    Each thread builds its own Drive service so connections are not shared.
    All heavy I/O (listing case folders and files) happens here in parallel.
    """
    svc = _get_thread_service(creds_path)

    client_diag   = diagnose_client(cf["name"])
    client_number = client_diag["client_number"]
    client_name   = client_diag["client_name"]

    result = {
        "unrecognized_client": None if client_diag["recognized"] else cf["name"],
        "failures":          [],
        "warnings":          [],
        "successful_parses": 0,
        "missing_tm":        [],
        "missing_class":     [],
        "missing_case_no":   [],
        "empty_cases":       [],
        "files_scanned":     0,
        "case_count":        0,
        # Each entry: {"key": tuple, "client_folder": str, "case_folder": str}
        "case_keys":         [],
    }

    case_folders = list_items(svc, cf["id"], mime_filter=FOLDER_MIME)

    for casf in case_folders:
        result["case_count"] += 1
        case_diag = diagnose_case(casf["name"])

        if case_diag["is_failure"]:
            result["failures"].append({
                "client_folder": cf["name"],
                "case_folder":   casf["name"],
                "issues":        "; ".join(case_diag["issues"]),
                "case_no":       case_diag["case_no"],
                "tm_no":         case_diag["tm_no"],
                "class_code":    case_diag["class_code"],
            })
        elif case_diag["is_warning"]:
            result["warnings"].append({
                "client_folder": cf["name"],
                "case_folder":   casf["name"],
                "warnings":      "; ".join(case_diag["warnings"]),
                "case_no":       case_diag["case_no"],
                "tm_no":         case_diag["tm_no"],
                "class_code":    case_diag["class_code"],
            })
        else:
            result["successful_parses"] += 1

        if not case_diag["tm_no"]:
            result["missing_tm"].append(casf["name"])
        if not case_diag["class_code"]:
            result["missing_class"].append(casf["name"])
        if not case_diag["case_no"]:
            result["missing_case_no"].append(casf["name"])

        # Record composite key — duplicate detection happens in the main thread
        # after all workers finish, to avoid locking around seen_keys dict.
        key = (
            client_number,
            client_name,
            case_diag["case_no"],
            case_diag["case_name"],
            case_diag["tm_no"],
            case_diag["class_code"],
        )
        result["case_keys"].append({
            "key":           key,
            "client_folder": cf["name"],
            "case_folder":   casf["name"],
        })

        # File listing — same skip rules as main.py
        files = list_items(svc, casf["id"])
        real_files = [
            f for f in files
            if f["mimeType"] != FOLDER_MIME
               and f["name"].lower() != "desktop.ini"
               and not f["name"].lower().endswith(".ini")
        ]
        result["files_scanned"] += len(real_files)
        if not real_files:
            result["empty_cases"].append(casf["name"])

    return result


def traverse_root(creds_path: str, root_folder_id: str, root_label: str,
                  stats: ValidationStats, workers: int = 12):
    """
    Traverse one root folder using a thread pool — one worker per client folder.
    Duplicate-key detection is done in the main thread after workers finish
    so it is never subject to race conditions.
    """
    stats.root_folders_scanned += 1
    print(f"\n   📁 Scanning root: {root_label}")

    # Build a single-use service just for listing client folders
    svc = build_drive_service(creds_path)
    client_folders = list_items(svc, root_folder_id, mime_filter=FOLDER_MIME)
    total_clients  = len(client_folders)
    print(f"      Found {total_clients} client folder(s) — scanning with {workers} parallel workers…")

    done_count = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {
            pool.submit(_process_client_folder, cf, creds_path): cf
            for cf in client_folders
        }
        for future in as_completed(future_map):
            done_count += 1
            if done_count % 100 == 0 or done_count == total_clients:
                elapsed = round(time.time() - stats.start_time, 1)
                print(f"      ↳ {done_count}/{total_clients} clients done  [{elapsed}s]")

            try:
                r = future.result()
            except Exception as exc:
                cf = future_map[future]
                print(f"      ⚠️  Worker error for {cf['name']!r}: {exc}")
                continue

            # Merge worker result into shared stats (main thread only — no locks needed)
            stats.client_folders_scanned += 1
            stats.case_folders_scanned   += r["case_count"]
            stats.files_scanned          += r["files_scanned"]
            stats.successful_parses      += r["successful_parses"]

            if r["unrecognized_client"]:
                stats.unrecognized_clients.append(r["unrecognized_client"])

            stats.failures.extend(r["failures"])
            stats.warnings.extend(r["warnings"])
            stats.missing_tm.extend(r["missing_tm"])
            stats.missing_class.extend(r["missing_class"])
            stats.missing_case_no.extend(r["missing_case_no"])
            stats.empty_cases.extend(r["empty_cases"])

            # Duplicate detection — main thread, no race risk
            for ci in r["case_keys"]:
                key = ci["key"]
                if key in stats.seen_keys:
                    stats.duplicates.append({
                        "client_folder":     ci["client_folder"],
                        "case_folder":       ci["case_folder"],
                        "first_seen_client": stats.seen_keys[key]["client"],
                        "first_seen_case":   stats.seen_keys[key]["case"],
                        "composite_key":     str(key),
                    })
                else:
                    stats.seen_keys[key] = {
                        "client": ci["client_folder"],
                        "case":   ci["case_folder"],
                    }
                    stats.records_generated += 1


# ─────────────────────────────────────────────────────────────────────────────
# Report generation
# ─────────────────────────────────────────────────────────────────────────────

def suggest(pattern: str) -> str:
    """
    Generate a parser-improvement suggestion from a structural token pattern.

    Uses the actual token vocabulary emitted by describe_token_pattern():
      [CASE_NO]  [TM_NO]  [CLASS]  [CLIENT_NO]  [SHORT_NUM]  [NUM]
      [UPPER]    [Word]   [DATE]   [OTHER]

    Checks for meaningful token combinations via substring matching so
    suggestions remain useful even for compound or novel patterns.
    """
    has_case   = "[CASE_NO]"   in pattern
    has_tm     = "[TM_NO]"     in pattern
    has_cls    = "[CLASS]"     in pattern
    has_client = "[CLIENT_NO]" in pattern
    has_short  = "[SHORT_NUM]" in pattern
    has_num    = "[NUM]"       in pattern
    has_upper  = "[UPPER]"     in pattern
    has_word   = "[Word]"      in pattern
    has_date   = "[DATE]"      in pattern
    has_other  = "[OTHER]"     in pattern

    # Ordered from most-specific to most-generic
    if has_case and has_short and not has_tm:
        return ("Short numeric value found where TM No expected — "
                "TM No must be exactly 6 digits. Check and pad or correct the number.")

    if has_case and has_num and not has_tm:
        return ("Non-6-digit number found where TM No expected — "
                "TM No must be exactly 6 consecutive digits.")

    if has_client and not has_case:
        return ("Folder looks like a client folder nested at case level — "
                "verify the directory depth (client → case, not client at case level).")

    if has_case and has_tm and not has_cls:
        return ("Case # and TM No parsed correctly but Class code is absent — "
                "append the class code (e.g. C01, C29) to the folder name.")

    if has_tm and not has_case:
        return ("TM No detected but Case # is missing — "
                "prepend the Case # (e.g. A001-001) before the case name.")

    if has_case and not has_tm and not has_cls:
        return ("Only Case # found — add 6-digit TM No and class code (e.g. C01) "
                "to the folder name so all fields can be extracted.")

    if has_date and not has_case:
        return ("Date token found but no Case # — folder may be a document "
                "dropped directly into the client folder rather than inside a case folder.")

    if has_upper and not has_case and not has_tm:
        return ("All-caps text with no structured codes — "
                "add Case # (e.g. A001-001), TM No (6 digits), and Class (e.g. C01).")

    if has_word and not has_case and not has_tm:
        return ("Plain words with no structured codes — "
                "confirm this is a case folder and add Case #, TM No, and Class.")

    if has_other and not has_case:
        return ("Unusual characters or mixed-case patterns detected — "
                "rename to follow the convention: CASE# CaseName TMNO CLASS.")

    # Final generic fallback based on what's missing
    missing = []
    if not has_case: missing.append("Case # (e.g. A001-001)")
    if not has_tm:   missing.append("TM No (6 digits)")
    if not has_cls:  missing.append("Class code (e.g. C01)")
    if missing:
        return f"Folder is missing: {', '.join(missing)}."
    return "Unusual token structure — review folder name against the naming convention."


def save_csv(rows: list[dict], path: Path, fieldnames: list[str] | None = None):
    if not rows:
        path.write_text("(no records)\n", encoding="utf-8")
        return
    fields = fieldnames or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def e(v) -> str:
    """HTML-escape and newline-safe."""
    return html.escape(str(v) if v is not None else "").replace("\n", "<br>")


def save_html(stats: ValidationStats, patterns: list[dict], out_path: Path,
              run_ts: str, root_labels: list[str]):

    dur = stats.duration_seconds

    def pct(n, total):
        return f"{(n/total*100):.1f}%" if total else "—"

    total_cases = stats.case_folders_scanned

    # Stat rows
    def stat_row(label, value, extra=""):
        extra_td = f'<td class="extra">{e(extra)}</td>' if extra else '<td></td>'
        return f'<tr><td class="lbl">{e(label)}</td><td class="val">{e(value)}</td>{extra_td}</tr>'

    stat_rows = "".join([
        stat_row("Root folders scanned",    stats.root_folders_scanned,   ", ".join(root_labels)),
        stat_row("Client folders scanned",  stats.client_folders_scanned),
        stat_row("Case folders scanned",    stats.case_folders_scanned),
        stat_row("Files scanned",           stats.files_scanned),
        stat_row("Records generated",       stats.records_generated),
        stat_row("Processing duration",     f"{dur}s"),
        stat_row("─── Parse Results ───",   ""),
        stat_row("Cases fully parsed",      stats.successful_parses,
                 pct(stats.successful_parses, total_cases)),
        stat_row("Parse warnings",          len(stats.warnings),
                 pct(len(stats.warnings), total_cases)),
        stat_row("Parse failures",          len(stats.failures),
                 pct(len(stats.failures), total_cases)),
        stat_row("─── Data Quality ───",    ""),
        stat_row("Duplicate records",       len(stats.duplicates)),
        stat_row("Empty case folders",      len(stats.empty_cases)),
        stat_row("Missing TM Number",       len(stats.missing_tm),
                 pct(len(stats.missing_tm), total_cases)),
        stat_row("Missing Class code",      len(stats.missing_class),
                 pct(len(stats.missing_class), total_cases)),
        stat_row("Missing Case Number",     len(stats.missing_case_no),
                 pct(len(stats.missing_case_no), total_cases)),
        stat_row("Unrecognized client folders", len(stats.unrecognized_clients)),
    ])

    # Pattern rows
    pattern_rows = ""
    all_bad = [f["case_folder"] for f in stats.failures] + [w["case_folder"] for w in stats.warnings]
    pats = top_n_patterns(all_bad, n=10)
    for i, p in enumerate(pats, 1):
        examples = "; ".join(e(ex) for ex in p["examples"])
        sug = e(suggest(p["pattern"]))
        pattern_rows += (
            f'<tr><td>{i}</td>'
            f'<td class="mono">{e(p["pattern"])}</td>'
            f'<td class="cnt">{p["count"]}</td>'
            f'<td>{examples}</td>'
            f'<td class="sug">{sug}</td></tr>\n'
        )

    # Failure rows (top 20)
    failure_rows = ""
    for f in stats.failures[:20]:
        failure_rows += (
            f'<tr class="fail">'
            f'<td>{e(f["client_folder"])}</td>'
            f'<td>{e(f["case_folder"])}</td>'
            f'<td>{e(f["issues"])}</td>'
            f'</tr>\n'
        )
    if len(stats.failures) > 20:
        failure_rows += f'<tr><td colspan="3"><em>… and {len(stats.failures)-20} more (see validation_failures.csv)</em></td></tr>\n'

    # Warning rows (top 20)
    warning_rows = ""
    for w in stats.warnings[:20]:
        warning_rows += (
            f'<tr class="warn">'
            f'<td>{e(w["client_folder"])}</td>'
            f'<td>{e(w["case_folder"])}</td>'
            f'<td>{e(w["warnings"])}</td>'
            f'</tr>\n'
        )
    if len(stats.warnings) > 20:
        warning_rows += f'<tr><td colspan="3"><em>… and {len(stats.warnings)-20} more (see validation_warnings.csv)</em></td></tr>\n'

    overall_ok = len(stats.failures) == 0 and len(stats.duplicates) == 0
    status_color = "#2d8a4e" if overall_ok else "#c0392b"
    status_text  = "✅ All records parsed cleanly" if overall_ok else f"⚠️  {len(stats.failures)} failure(s), {len(stats.duplicates)} duplicate(s)"

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Brandex Drive — Validation Report</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body   {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; background: #f4f6f9; color: #222; }}
    .hdr   {{ background: #1a3a5c; color: #fff; padding: 24px 36px; }}
    .hdr h1{{ margin: 0 0 6px; font-size: 1.45rem; }}
    .hdr p {{ margin: 0; font-size: .88rem; opacity: .78; }}
    .badge {{ display: inline-block; margin-top: 12px; padding: 5px 14px; border-radius: 20px;
              font-size: .85rem; font-weight: 600; background: {status_color}; color: #fff; }}
    .wrap  {{ padding: 24px 36px 36px; }}
    h2     {{ font-size: 1.1rem; color: #1a3a5c; border-bottom: 2px solid #1a3a5c; padding-bottom: 6px; margin-top: 32px; }}
    table  {{ width: 100%; border-collapse: collapse; background: #fff;
              box-shadow: 0 1px 4px rgba(0,0,0,.1); border-radius: 8px; overflow: hidden; margin-bottom: 20px; }}
    th     {{ background: #1a3a5c; color: #fff; padding: 9px 14px; text-align: left; font-size: .82rem; }}
    td     {{ padding: 8px 14px; font-size: .83rem; border-bottom: 1px solid #eee; vertical-align: top; }}
    tr:last-child td {{ border-bottom: none; }}
    .lbl   {{ width: 260px; font-weight: 600; }}
    .val   {{ width: 100px; }}
    .extra {{ color: #666; font-size: .78rem; }}
    .mono  {{ font-family: monospace; font-size: .78rem; white-space: pre-wrap; }}
    .cnt   {{ text-align: center; }}
    .sug   {{ color: #555; }}
    .fail td {{ background: #fdf2f0; }}
    .warn td {{ background: #fef9ec; }}
    .fail td:nth-child(3) {{ color: #c0392b; font-size: .78rem; }}
    .warn td:nth-child(3) {{ color: #d68910; font-size: .78rem; }}
    .note  {{ background: #fff8e1; border-left: 4px solid #f39c12; padding: 12px 18px;
              border-radius: 4px; font-size: .85rem; margin-bottom: 16px; }}
  </style>
</head>
<body>
  <div class="hdr">
    <h1>&#x1F5C2;&#xFE0F; Brandex Drive &mdash; Validation Report</h1>
    <p>Generated: {e(run_ts)} &nbsp;|&nbsp; Duration: {dur}s</p>
    <div class="badge">{status_text}</div>
  </div>
  <div class="wrap">

    <div class="note">
      &#x2139;&#xFE0F; This report validates <b>parser behaviour only</b>. No project code was modified.
      Confirmed bugs are documented in the Recommendations section.
    </div>

    <h2>Summary Statistics</h2>
    <table>
      <thead><tr><th>Metric</th><th>Count</th><th>% of Cases</th></tr></thead>
      <tbody>{stat_rows}</tbody>
    </table>

    <h2>Top Unrecognised Folder Patterns &amp; Suggested Fixes</h2>
    <table>
      <thead>
        <tr><th>#</th><th>Pattern</th><th>Count</th><th>Examples</th><th>Suggested Improvement</th></tr>
      </thead>
      <tbody>{pattern_rows if pattern_rows else '<tr><td colspan="5"><em>No unrecognised patterns — all folders parsed.</em></td></tr>'}</tbody>
    </table>

    <h2>Parse Failures <small style="font-weight:400;font-size:.8rem">(see validation_failures.csv for full list)</small></h2>
    <table>
      <thead><tr><th>Client Folder</th><th>Case Folder</th><th>Issues</th></tr></thead>
      <tbody>{failure_rows if failure_rows else '<tr class="fail"><td colspan="3"><em>No failures.</em></td></tr>'}</tbody>
    </table>

    <h2>Parse Warnings <small style="font-weight:400;font-size:.8rem">(see validation_warnings.csv for full list)</small></h2>
    <table>
      <thead><tr><th>Client Folder</th><th>Case Folder</th><th>Warnings</th></tr></thead>
      <tbody>{warning_rows if warning_rows else '<tr class="warn"><td colspan="3"><em>No warnings.</em></td></tr>'}</tbody>
    </table>

  </div>
</body>
</html>
"""
    out_path.write_text(html_doc, encoding="utf-8")
    print(f"   🌐 HTML report      : {out_path}")


def save_md(stats: ValidationStats, patterns: list[dict], out_path: Path,
            run_ts: str, root_labels: list[str]):

    total_cases = stats.case_folders_scanned

    def pct(n):
        return f"{(n/total_cases*100):.1f}%" if total_cases else "—"

    all_bad = [f["case_folder"] for f in stats.failures] + [w["case_folder"] for w in stats.warnings]
    pats    = top_n_patterns(all_bad, n=10)

    lines = [
        "# Brandex Drive — Validation Report",
        "",
        f"**Generated:** {run_ts}  ",
        f"**Duration:** {stats.duration_seconds}s  ",
        f"**Root folders:** {', '.join(root_labels)}",
        "",
        "---",
        "",
        "## Summary Statistics",
        "",
        "| Metric | Count | % of Cases |",
        "|---|---|---|",
        f"| Root folders scanned | {stats.root_folders_scanned} | — |",
        f"| Client folders scanned | {stats.client_folders_scanned} | — |",
        f"| Case folders scanned | {stats.case_folders_scanned} | — |",
        f"| Files scanned | {stats.files_scanned} | — |",
        f"| Records generated | {stats.records_generated} | — |",
        f"| **Cases fully parsed** | **{stats.successful_parses}** | **{pct(stats.successful_parses)}** |",
        f"| Parse warnings | {len(stats.warnings)} | {pct(len(stats.warnings))} |",
        f"| Parse failures | {len(stats.failures)} | {pct(len(stats.failures))} |",
        f"| Duplicate records | {len(stats.duplicates)} | — |",
        f"| Empty case folders | {len(stats.empty_cases)} | — |",
        f"| Missing TM Number | {len(stats.missing_tm)} | {pct(len(stats.missing_tm))} |",
        f"| Missing Class code | {len(stats.missing_class)} | {pct(len(stats.missing_class))} |",
        f"| Missing Case Number | {len(stats.missing_case_no)} | {pct(len(stats.missing_case_no))} |",
        f"| Unrecognized client folders | {len(stats.unrecognized_clients)} | — |",
        "",
        "---",
        "",
        "## Top 10 Unrecognised Folder Naming Patterns",
        "",
    ]

    if pats:
        lines += [
            "| # | Pattern | Count | Examples | Suggested Improvement |",
            "|---|---|---|---|---|",
        ]
        for i, p in enumerate(pats, 1):
            examples = "; ".join(p["examples"][:2])
            sug      = suggest(p["pattern"])
            lines.append(f"| {i} | `{p['pattern']}` | {p['count']} | {examples} | {sug} |")
    else:
        lines.append("_No unrecognised patterns — all folders parsed successfully._")

    lines += [
        "",
        "---",
        "",
        "## Recommendations",
        "",
    ]

    recs = []
    if stats.failures:
        recs.append(
            f"- **{len(stats.failures)} case folders could not be parsed.** "
            "These will produce empty Case # and/or TM No in exports. "
            "Rename the folders to match the pattern: `XNNN-NNN CaseName 123456 C01`."
        )
    if stats.missing_tm:
        recs.append(
            f"- **{len(stats.missing_tm)} cases are missing TM Numbers.** "
            "The parser expects exactly 6 consecutive digits in the folder name. "
            "5-digit or 7-digit values will not be captured."
        )
    if stats.missing_class:
        recs.append(
            f"- **{len(stats.missing_class)} cases have no Class code.** "
            "Class codes must follow the pattern `C` + digits (e.g. `C01`, `C29`). "
            "Codes like `CL01`, `Class-1`, or `Class01` will not match."
        )
    if stats.duplicates:
        recs.append(
            f"- **{len(stats.duplicates)} duplicate composite keys detected.** "
            "Two case folders that produce the same (CLIENT NUMBER, CASE #, TM NO, CLASS) "
            "will be silently merged into a single record. "
            "Rename one of the conflicting folders or confirm they are genuinely the same case."
        )
    if stats.empty_cases:
        recs.append(
            f"- **{len(stats.empty_cases)} case folders contain no files.** "
            "These produce no pattern tick-marks. If they are placeholders, "
            "consider removing them or adding at least one document."
        )
    if stats.unrecognized_clients:
        recs.append(
            f"- **{len(stats.unrecognized_clients)} client folders do not match the expected pattern.** "
            "Client folders must start with a letter-dash-number prefix like `A-001`. "
            f"Unrecognized: {', '.join(stats.unrecognized_clients[:5])}"
            + (f" … (+{len(stats.unrecognized_clients)-5} more)" if len(stats.unrecognized_clients) > 5 else "")
        )

    if not recs:
        lines.append("_No issues found. Dataset is clean._")
    else:
        lines.extend(recs)

    lines += [
        "",
        "---",
        "",
        "## Output Files",
        "",
        "| File | Contents |",
        "|---|---|",
        "| `validation_report.html` | Human-readable colour-coded summary |",
        "| `validation_report.md` | This file — statistics + recommendations |",
        "| `validation_warnings.csv` | All partial-parse warnings (one row per case) |",
        "| `validation_failures.csv` | All complete-parse failures (one row per case) |",
        "",
        "---",
        "",
        "_Generated by `validate_drive.py` — no project code was modified._",
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"   📝 Markdown report  : {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Validate Drive Folders List parser against live Brandex Google Drive data"
    )
    parser.add_argument(
        "--clients-id",
        metavar="FOLDER_ID",
        help="Google Drive folder ID for '1 ALL CLIENTS' (get from Drive URL)"
    )
    parser.add_argument(
        "--consultants-id",
        metavar="FOLDER_ID",
        help="Google Drive folder ID for '2 CONSULTANTS' (optional)"
    )
    parser.add_argument(
        "--search-name",
        metavar="NAME",
        action="append",
        help="Search for a root folder by name instead of ID (can repeat)"
    )
    parser.add_argument(
        "--creds",
        default=str(BASE_DIR / "credentials.json"),
        help="Path to Google Service Account credentials.json (default: ./credentials.json)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=12,
        metavar="N",
        help="Parallel worker threads for client-folder traversal (default: 12)"
    )
    args = parser.parse_args()

    print("🔐 Authenticating with Google Drive…")
    service = build_drive_service(args.creds)
    print("   ✅ Connected")

    # Resolve root folder IDs
    roots: list[tuple[str, str]] = []  # (folder_id, label)

    if args.clients_id:
        roots.append((args.clients_id, "1 ALL CLIENTS"))
    if args.consultants_id:
        roots.append((args.consultants_id, "2 CONSULTANTS"))

    if args.search_name:
        for name in args.search_name:
            print(f"   🔍 Searching for folder: {name!r}")
            fid = find_folder_by_name(service, name)
            if fid:
                print(f"      Found → {fid}")
                roots.append((fid, name))
            else:
                print(f"      ❌ Not found — check that the folder is shared with the service account.")

    # If no roots specified, try the default folder names from main.py
    if not roots:
        print("\n📂 No folder IDs provided — searching for default folder names…")
        for name in ("1 ALL CLIENTS", "2 CONSULTANTS"):
            print(f"   🔍 Searching: {name!r}")
            fid = find_folder_by_name(service, name)
            if fid:
                print(f"      Found → {fid}")
                roots.append((fid, name))
            else:
                print(f"      ⚠️  Not found: {name!r}")
                print(f"         Make sure the folder is shared with the service account, or pass --clients-id / --consultants-id")

    if not roots:
        print("\n❌ No accessible root folders found.")
        print("   Share the Drive folders with your service account email and retry,")
        print("   or pass folder IDs directly: --clients-id ID --consultants-id ID")
        sys.exit(1)

    # Traverse
    stats  = ValidationStats()
    run_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n🚀 Starting traversal of {len(roots)} root folder(s)  (workers={args.workers})…")
    for folder_id, label in roots:
        traverse_root(args.creds, folder_id, label, stats, workers=args.workers)

    stats.finish()
    root_labels = [label for _, label in roots]

    print(f"\n📊 Traversal complete in {stats.duration_seconds}s")
    print(f"   Clients  : {stats.client_folders_scanned}")
    print(f"   Cases    : {stats.case_folders_scanned}")
    print(f"   Files    : {stats.files_scanned}")
    print(f"   Records  : {stats.records_generated}")
    print(f"   Failures : {len(stats.failures)}")
    print(f"   Warnings : {len(stats.warnings)}")
    print(f"   Dupes    : {len(stats.duplicates)}")

    # Gather unparsed patterns for report
    all_bad = [f["case_folder"] for f in stats.failures] + [w["case_folder"] for w in stats.warnings]
    patterns = top_n_patterns(all_bad, n=10)

    # Save outputs
    print("\n💾 Saving reports…")
    save_html(stats, patterns, EXPORT_DIR / "validation_report.html", run_ts, root_labels)
    save_md(stats, patterns,   EXPORT_DIR / "validation_report.md",   run_ts, root_labels)

    save_csv(
        stats.warnings,
        EXPORT_DIR / "validation_warnings.csv",
        fieldnames=["client_folder", "case_folder", "warnings", "case_no", "tm_no", "class_code"],
    )
    print(f"   ⚠️  Warnings CSV     : {EXPORT_DIR / 'validation_warnings.csv'}  ({len(stats.warnings)} rows)")

    save_csv(
        stats.failures,
        EXPORT_DIR / "validation_failures.csv",
        fieldnames=["client_folder", "case_folder", "issues", "case_no", "tm_no", "class_code"],
    )
    print(f"   ❌ Failures CSV     : {EXPORT_DIR / 'validation_failures.csv'}  ({len(stats.failures)} rows)")

    print("\n✅ Done.")


if __name__ == "__main__":
    main()
