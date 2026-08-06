import os
import re
import threading
import pandas as pd
from pathlib import Path
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk

# ─── App Appearance ───────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ─── Base Paths ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()
EXPORT_DIR = str(BASE_DIR / "export")
os.makedirs(EXPORT_DIR, exist_ok=True)

# ─── Google Sheets Config ─────────────────────────────────────────────────────
SHEET_ID   = "1yu27k_3Z6cCJmcnQI52z1dIC52Zi9ZxaKlo9wJiNFiQ"
SHEET_NAME = "List"
SCOPES     = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Default paths (user can override via GUI)
DEFAULT_CLIENTS_PATH     = r"F:\Br004\My Drive\1 ALL CLIENTS"
DEFAULT_CONSULTANTS_PATH = r"F:\Br004\My Drive\2 CONSULTANTS"

# ══════════════════════════════════════════════════════════════════════════════
#  PARSING HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def parse_client_folder(folder_name):
    """Extract (client_number, client_name) from a client folder name."""
    match = re.match(r'^([A-Z]-\d+)\s+(.+)$', folder_name)
    if match:
        return match.group(1), match.group(2)
    return "", folder_name


def parse_case_folder(folder_name):
    """Extract (case_no, case_name, tm_no, class_code) from a case folder name."""
    parts = folder_name.split()
    case_no = case_name = tm_no = class_code = ""
    for part in parts:
        if re.match(r'^[A-Z]\d{3}-\d{3}$', part):
            case_no = part
        elif case_no and not case_name and re.match(r'^[A-Z][a-zA-Z]+$', part):
            case_name = part
        elif re.match(r'^\d{6}$', part):
            tm_no = part
        elif re.match(r'^[C]\d+$', part):
            class_code = part
    return case_no, case_name, tm_no, class_code


def extract_full_case_name(folder_name, tm_no):
    """Extract full case name using TM number as a right-side delimiter."""
    if not tm_no:
        return ""
    match = re.search(rf'\b{tm_no}\b', folder_name)
    if match:
        parts = folder_name.split()
        case_name_parts = []
        found_case_no = False
        for part in parts:
            if re.match(r'^[A-Z]\d{3}-\d{3}$', part):
                found_case_no = True
                continue
            elif found_case_no and part != tm_no and not re.match(r'^[C]\d+$', part):
                case_name_parts.append(part)
            elif part == tm_no:
                break
        return " ".join(case_name_parts)
    return ""


# ══════════════════════════════════════════════════════════════════════════════
#  PATTERN MATCHING  — 20 Rules
# ══════════════════════════════════════════════════════════════════════════════

ALL_PATTERNS = {
    # ── Original 13 ───────────────────────────────────────────────────────────
    'TM-1': [
        r'\bTM-1\b', r'\bTM1\b', r'\(TM-1\)', r'\[TM-1\]'
    ],
    'TM-48': [
        r'\bTM-48\b', r'\bTM48\b', r'\(TM-48\)', r'\[TM-48\]',
        r'UPDATED\s*\[TM-48\]', r'UPDATED\s*X\s*\[TM-48\]',
        r'TM-48\s*-\s*COPY', r'TM-48\s*-\s*COPY\s*-\s*COPY'
    ],
    'EXAM': [
        r'\bTM-48\b', r'\bTM48\b', r'\bEXAMINATION\b', r'\bSHOWCASE\b',
        r'SHOWCASE\s*NOTICE', r'17\(2\)\(B\)', r'14\(3\)\(A\)', r'14\(1\)\(b\)',
        r'\bREPLY\b', r'REPLY\s*OF\s*NOTICE', r'MULTIPAL\s*REPLIES',
        r'17\(2\)\(B\),\s*14\(3\)\(A\)\s*&\s*14\(1\)\(B\)',
        r'17\(2\)\(B\),\s*14\(3\)\(A\),\s*14\s*\(1\)\s*\(B\).*AND\s*14\(1\)\(C\)',
        r'REPLY\s*\[.*?\]\s*\(\d{2}-\d{2}-\d{4}\)'
    ],
    'ACK': [
        r'\bACK\b', r'ACKNOWLEDGMENT', r'ACKNOLDGEMENT',
        r'ACK\s*-\s*A\d{3}-\d{3}.*?C\d{2}.*?\d{2}-\w{3}-\d{4}'
    ],
    'ACCEPTANCE': [
        r'\bACCEPTANCE\b', r'ACCEPTANCE\s*DONE', r'COMPLETE\s*FILE'
    ],
    'D-NOTE': [
        r'\bTM-11\b', r'\bTM11\b', r'IPO-PAKISTAN\s*__\s*TM\s*11', r'TM\s*11',
        r'DEMAND\s*NOTE'
    ],
    'TM-16': [
        r'\bTM-16\b', r'\bTM16\b', r'IPO-PAKISTAN\s*__\s*TM\s*16', r'TM\s*16'
    ],
    'TM-50': [
        r'\bTM-50\b', r'\bTM50\b', r'IPO-PAKISTAN\s*__\s*TM\s*50', r'TM\s*50'
    ],
    'TM-06': [
        r'IPO-PAKISTAN\s*__\s*TM\s*06', r'IPO-PAKISTAN\s*__\s*TM\s*\d{2}'
    ],
    'COMPANY': [
        r'BOARD\s*OF\s*RESULOTION', r'BOARD\s*OF\s*RESOLUTION'
    ],
    'OPPO': [
        r'WITHDRAWN\s*LETTER', r'\bOPPOSITION\b', r'OPPO\b',
        r'GROUNDS\s*OF\s*OPPOSITION'
    ],
    'PUB': [
        r'\bPublication\b', r'\bPUBLICATION\b', r'JOURNAL\s*PUBLICATION',
        r'JOURNAL\s*CONVERT'
    ],
    'CERTIFICATE': [
        r'\bCERTIFICATE\b', r'CERTIFICATE\s*WITH\s*SIGN',
        r'ORIGINAL\s*CERTIFICATE', r'TRADE\s*MARK\s*CERTIFICATE',
        r'RENEWAL\s*CERTIFICATE'
    ],
    # ── 7 New Rules ───────────────────────────────────────────────────────────
    'LEGAL NOTICE': [
        r'LEGAL\s*NOTICE', r'LEGAL\s*NOTIC\b'
    ],
    'E-STAMP': [
        r'\bE-STAMP\b', r'\bESTAMP\b', r'\bSTAMP\b'
    ],
    'ID / CNIC': [
        r'\bCNIC\b', r'\bNIC\b', r'\bID\b', r'\bNTN\b',
        r'^ID\s*[BF]$', r'\bPASSPORT\b'
    ],
    'AFFIDAVIT': [
        r'\bAFFIDAVIT\b', r'\bAFFIDVITE\b'
    ],
    'POA': [
        r'POWER\s*OF\s*ATTORNEY', r'WAQALATNAMA', r'\bPOA\b',
        r'AUTHORITY\s*LETTER'
    ],
    'LEDGER': [
        r'\bLEDGER\b', r'LED-PERONALS', r'DB\s*JOURNALS',
        r'JOURNAL\s*\d+', r'FBR\s*LIST'
    ],
    'DATA SHEET': [
        r'DATA\s*SHEET', r'DATA\s*SHEET\s*PRINT', r'X000\s*COMPANY\s*DATA\s*SHEET'
    ],
}

# Column order for export
ALL_COLUMNS = [
    "CLIENT NUMBER", "CLIENT NAME", "CASE #", "CASE NAME", "TM NO", "CLASS",
    "FILES", "EXT",
    "TM-1", "TM-48", "EXAM", "ACK", "ACCEPTANCE", "D-NOTE",
    "TM-16", "TM-50", "TM-06", "COMPANY", "OPPO", "PUB", "CERTIFICATE",
    "LEGAL NOTICE", "E-STAMP", "ID / CNIC", "AFFIDAVIT", "POA", "LEDGER",
    "DATA SHEET",
    "DATE ADDED"
]

SHEET_HEADERS = [
    "📋 CLIENT NUMBER", "👤 CLIENT NAME", "📁 CASE #", "📝 CASE NAME",
    "🔢 TM NO", "📚 CLASS", "📎 FILES", "📄 EXT",
    "📄 TM-1", "📄 TM-48", "📝 EXAM", "✅ ACK", "✅ ACCEPTANCE",
    "📋 D-NOTE", "📄 TM-16", "📄 TM-50", "📄 TM-06",
    "🏢 COMPANY", "❌ OPPO", "📰 PUB", "📜 CERTIFICATE",
    "⚖️ LEGAL NOTICE", "📮 E-STAMP", "🪪 ID / CNIC", "📃 AFFIDAVIT",
    "✍️ POA", "📒 LEDGER", "📊 DATA SHEET",
    "📅 DATE ADDED"
]


def check_file_patterns(file_names):
    """Check file names against all patterns and return tickmarks."""
    file_list = file_names.split('\n') if file_names else []
    all_files_text = " ".join(file_list)

    def _match(text, pattern_list):
        if not text:
            return False
        text = str(text).upper()
        return any(re.search(p, text, re.IGNORECASE) for p in pattern_list)

    return {
        cat: "✓" if _match(all_files_text, pats) else ""
        for cat, pats in ALL_PATTERNS.items()
    }


# ══════════════════════════════════════════════════════════════════════════════
#  DIRECTORY PROCESSING  (deep or fast scan)
# ══════════════════════════════════════════════════════════════════════════════

def process_directory(base_path, prefix_to_remove, max_records=None, deep_scan=True):
    """
    Scan base_path and return a list of record dicts.
    deep_scan=True  → recursive os.walk (finds all nested files)
    deep_scan=False → strict 2-level scan (Client / Case) — much faster on large drives
    """
    case_groups = {}
    processed_count = 0

    if deep_scan:
        # ── Recursive scan ─────────────────────────────────────────────────
        for root, dirs, files in os.walk(base_path):
            if max_records and processed_count >= max_records:
                break
            if not files:
                continue

            rel_path = os.path.relpath(root, base_path)
            components = [] if rel_path == '.' else rel_path.split(os.sep)

            client_folder = components[0] if len(components) > 0 else ""
            case_folder   = components[1] if len(components) > 1 else ""

            client_number, client_name = (
                parse_client_folder(client_folder) if client_folder
                else ("", "Root/Uncategorized")
            )
            case_no, case_name, tm_no, class_code = (
                parse_case_folder(case_folder) if case_folder
                else ("", "No Case Folder", "", "")
            )

            if tm_no and case_folder:
                full = extract_full_case_name(case_folder, tm_no)
                if full:
                    case_name = full

            case_key  = (client_number, client_name, case_no, case_name, tm_no, class_code)
            valid_files = _collect_files(files)

            if valid_files:
                if case_key not in case_groups:
                    case_groups[case_key] = []
                    processed_count += 1
                case_groups[case_key].extend(valid_files)
    else:
        # ── Fast 2-level scan ──────────────────────────────────────────────
        for client_folder in os.listdir(base_path):
            if max_records and processed_count >= max_records:
                break
            client_path = os.path.join(base_path, client_folder)
            if not os.path.isdir(client_path):
                continue

            client_number, client_name = parse_client_folder(client_folder)

            for case_folder in os.listdir(client_path):
                if max_records and processed_count >= max_records:
                    break
                case_path = os.path.join(client_path, case_folder)
                if not os.path.isdir(case_path):
                    continue

                case_no, case_name, tm_no, class_code = parse_case_folder(case_folder)
                full = extract_full_case_name(case_folder, tm_no)
                if full:
                    case_name = full

                case_key = (client_number, client_name, case_no, case_name, tm_no, class_code)
                valid_files = _collect_files(os.listdir(case_path))

                if case_key not in case_groups:
                    case_groups[case_key] = []
                    processed_count += 1
                case_groups[case_key].extend(valid_files)

    # ── Build records ──────────────────────────────────────────────────────
    records = []
    for (client_number, client_name, case_no, case_name, tm_no, class_code), files in case_groups.items():
        file_names = "\n".join([f.split("|")[0] for f in files if f.split("|")[0]])
        file_exts  = "\n".join([f.split("|")[1] for f in files if f.split("|")[1]])

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
        record.update(check_file_patterns(file_names))
        records.append(record)

    return records


def _collect_files(file_list):
    """Filter + format a list of file names to 'name|ext' pairs."""
    result = []
    for f in file_list:
        if f.lower() == 'desktop.ini':
            continue
        name, ext = os.path.splitext(f)
        if ext.lower() == '.ini':
            ext = ''
        result.append(f"{name}|{ext.lstrip('.')}")
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  GOOGLE SHEETS
# ══════════════════════════════════════════════════════════════════════════════

def get_google_sheets_client():
    """Initialize Google Sheets client using credentials.json next to this script."""
    try:
        creds_path = str(BASE_DIR / "credentials.json")
        if not os.path.exists(creds_path):
            return None, f"❌ credentials.json not found at: {creds_path}"
        creds  = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client, None
    except Exception as e:
        return None, f"Error connecting to Google Sheets: {e}"


def setup_sheet_headers(sheet):
    """Create / reset worksheet headers."""
    try:
        try:
            worksheet = sheet.worksheet(SHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=SHEET_NAME, rows="2000", cols=str(len(SHEET_HEADERS)))
        col_end   = chr(ord('A') + len(SHEET_HEADERS) - 1)
        worksheet.update(values=[SHEET_HEADERS], range_name=f'A1:{col_end}1')
        return worksheet, None
    except Exception as e:
        return None, str(e)


def upload_to_sheets(records, log_fn=print):
    """Upload records to Google Sheets."""
    client, err = get_google_sheets_client()
    if err:
        log_fn(err)
        return False

    try:
        sheet = client.open_by_key(SHEET_ID)
        worksheet, err = setup_sheet_headers(sheet)
        if err:
            log_fn(f"❌ Header error: {err}")
            return False
        if not records:
            log_fn("✅ No records to upload.")
            return True

        data_cols = [c for c in ALL_COLUMNS if c not in ("CLIENT NUMBER", "CLIENT NAME", "CASE #",
                                                           "CASE NAME", "TM NO", "CLASS", "FILES",
                                                           "EXT", "DATE ADDED")]
        data = []
        for r in records:
            row = [
                r.get('CLIENT NUMBER', ''), r.get('CLIENT NAME', ''),
                r.get('CASE #', ''),        r.get('CASE NAME', ''),
                r.get('TM NO', ''),         r.get('CLASS', ''),
                r.get('FILES', ''),         r.get('EXT', ''),
            ] + [r.get(c, '') for c in ALL_PATTERNS.keys()] + [r.get('DATE ADDED', '')]
            data.append(row)

        worksheet.append_rows(data)
        log_fn(f"✅ Uploaded {len(records)} records to Google Sheets")
        return True
    except Exception as e:
        log_fn(f"❌ Google Sheets error: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  LOCAL EXPORT
# ══════════════════════════════════════════════════════════════════════════════

SHORT_NAMES = {
    "consultants_data": "cons_patterns",
    "clients_data":     "clients_patterns",
    "all_data":         "all_patterns",
    "custom_data":      "custom_patterns",
}


def export_local(records, filename_prefix, log_fn=print):
    """Export records to Excel + CSV."""
    if not records:
        log_fn("No records to export!")
        return

    df = pd.DataFrame(records)
    # Only keep columns that exist in the dataframe
    existing_cols = [c for c in ALL_COLUMNS if c in df.columns]
    df = df[existing_cols]

    short = SHORT_NAMES.get(filename_prefix, filename_prefix)
    excel_path = os.path.join(EXPORT_DIR, f"{short}.xlsx")
    csv_path   = os.path.join(EXPORT_DIR, f"{short}.csv")

    df.to_excel(excel_path, index=False, engine='openpyxl')
    df.to_csv(csv_path, index=False)

    log_fn(f"💾 Exported {len(df)} records")
    log_fn(f"   📊 Excel: {excel_path}")
    log_fn(f"   📄 CSV:   {csv_path}")


def handle_upload(records, filename_prefix, export_local_flag, export_sheets_flag, log_fn=print):
    """Route records to the chosen destinations."""
    if not records:
        log_fn("❌ No records to process!")
        return
    if export_local_flag:
        export_local(records, filename_prefix, log_fn)
    if export_sheets_flag:
        upload_to_sheets(records, log_fn)


# ══════════════════════════════════════════════════════════════════════════════
#  CUSTOMTKINTER GUI
# ══════════════════════════════════════════════════════════════════════════════

class DriveDataApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ── Window setup ──────────────────────────────────────────────────
        self.title("🗂️ Drive Folders — Pattern Matcher")
        self.geometry("900x760")
        self.minsize(820, 680)
        self.resizable(True, True)

        # State vars
        self._running = False
        self.clients_path     = ctk.StringVar(value=DEFAULT_CLIENTS_PATH)
        self.consultants_path = ctk.StringVar(value=DEFAULT_CONSULTANTS_PATH)
        self.custom_path      = ctk.StringVar(value="")
        self.max_records_var  = ctk.StringVar(value="")   # empty = all
        self.deep_scan_var    = ctk.BooleanVar(value=True)
        self.export_local_var  = ctk.BooleanVar(value=True)
        self.export_sheets_var = ctk.BooleanVar(value=True)

        self._build_ui()

    # ── UI Construction ───────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # ─ Header ─────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, corner_radius=12, fg_color=("#1a1a2e", "#1a1a2e"))
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(hdr, text="🗂️  Drive Folders — Pattern Matcher",
                     font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
                     text_color="#60a5fa").grid(row=0, column=0, pady=(14, 2))
        ctk.CTkLabel(hdr,
                     text=f"20 pattern rules  •  Deep & Fast scan modes  •  Google Sheets + Local export",
                     font=ctk.CTkFont(size=12), text_color="#94a3b8").grid(row=1, column=0, pady=(0, 14))

        # ─ Config Panel ───────────────────────────────────────────────────
        cfg = ctk.CTkFrame(self, corner_radius=12)
        cfg.grid(row=1, column=0, sticky="ew", padx=16, pady=4)
        cfg.grid_columnconfigure(1, weight=1)

        # Paths
        self._path_row(cfg, "📁 Clients Path",      self.clients_path,     0, self._browse_clients)
        self._path_row(cfg, "📁 Consultants Path",  self.consultants_path, 1, self._browse_consultants)
        self._path_row(cfg, "📂 Custom Path",        self.custom_path,      2, self._browse_custom)

        # Options row
        opt = ctk.CTkFrame(cfg, fg_color="transparent")
        opt.grid(row=3, column=0, columnspan=3, sticky="ew", padx=12, pady=(6, 10))
        opt.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        ctk.CTkLabel(opt, text="Max Records (blank = all):",
                     font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="e", padx=(0, 6))
        ctk.CTkEntry(opt, textvariable=self.max_records_var, width=90,
                     placeholder_text="e.g. 200").grid(row=0, column=1, sticky="w")

        ctk.CTkSwitch(opt, text="🔍 Deep Scan", variable=self.deep_scan_var,
                      onvalue=True, offvalue=False,
                      font=ctk.CTkFont(size=12)).grid(row=0, column=2, padx=20)

        ctk.CTkCheckBox(opt, text="💾 Export Local",
                        variable=self.export_local_var,
                        font=ctk.CTkFont(size=12)).grid(row=0, column=3, padx=8)
        ctk.CTkCheckBox(opt, text="🌐 Google Sheets",
                        variable=self.export_sheets_var,
                        font=ctk.CTkFont(size=12)).grid(row=0, column=4, padx=8)

        # ─ Action Buttons ─────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, corner_radius=12)
        btn_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=4)
        btn_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        btn_spec = [
            ("👥 ALL CLIENTS",       "#2563eb", self._run_clients),
            ("🤝 CONSULTANTS",       "#7c3aed", self._run_consultants),
            ("📦 BOTH",              "#0f766e", self._run_both),
            ("📂 CUSTOM PATH",       "#b45309", self._run_custom),
            ("⚡ Quick Export",      "#1e3a5f", self._run_quick),
        ]
        for col, (lbl, color, cmd) in enumerate(btn_spec):
            ctk.CTkButton(btn_frame, text=lbl, fg_color=color,
                          hover_color=self._darken(color),
                          font=ctk.CTkFont(size=13, weight="bold"),
                          height=42, corner_radius=8,
                          command=cmd).grid(row=0, column=col,
                                            padx=8, pady=10, sticky="ew")

        # ─ Progress ───────────────────────────────────────────────────────
        self.progress = ctk.CTkProgressBar(self, mode="indeterminate", height=6)
        self.progress.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 2))
        self.progress.set(0)

        # ─ Log Console ────────────────────────────────────────────────────
        log_frame = ctk.CTkFrame(self, corner_radius=12)
        log_frame.grid(row=4, column=0, sticky="nsew", padx=16, pady=(2, 16))
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(4, weight=1)

        log_hdr = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_hdr.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 0))
        log_hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(log_hdr, text="📋 Status Log",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#94a3b8").grid(row=0, column=0, sticky="w")
        ctk.CTkButton(log_hdr, text="Clear", width=60, height=24,
                      fg_color="#374151", hover_color="#4b5563",
                      font=ctk.CTkFont(size=11),
                      command=self._clear_log).grid(row=0, column=1)

        self.log_box = ctk.CTkTextbox(log_frame, font=ctk.CTkFont(family="Consolas", size=12),
                                      wrap="word", state="disabled",
                                      fg_color=("#1e293b", "#0f172a"),
                                      text_color="#e2e8f0")
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4, 10))

        self._log("✅ Application ready. Select a scan mode above.")

    # ── Path row helper ───────────────────────────────────────────────────

    def _path_row(self, parent, label, var, row, browse_cmd):
        ctk.CTkLabel(parent, text=label,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     width=150, anchor="e").grid(row=row, column=0, padx=(12, 6), pady=4, sticky="e")
        ctk.CTkEntry(parent, textvariable=var, font=ctk.CTkFont(size=11)
                     ).grid(row=row, column=1, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(parent, text="Browse…", width=80, height=28,
                      fg_color="#374151", hover_color="#4b5563",
                      font=ctk.CTkFont(size=11),
                      command=browse_cmd).grid(row=row, column=2, padx=(4, 12), pady=4)

    # ── Browse callbacks ──────────────────────────────────────────────────

    def _browse_clients(self):
        p = filedialog.askdirectory(title="Select ALL CLIENTS folder")
        if p:
            self.clients_path.set(p)

    def _browse_consultants(self):
        p = filedialog.askdirectory(title="Select CONSULTANTS folder")
        if p:
            self.consultants_path.set(p)

    def _browse_custom(self):
        p = filedialog.askdirectory(title="Select custom folder")
        if p:
            self.custom_path.set(p)

    # ── Log helpers ───────────────────────────────────────────────────────

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{ts}] {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    # ── Progress ──────────────────────────────────────────────────────────

    def _start_progress(self):
        self.progress.configure(mode="indeterminate")
        self.progress.start()

    def _stop_progress(self):
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress.set(1)

    # ── Max records ───────────────────────────────────────────────────────

    def _get_max(self):
        v = self.max_records_var.get().strip()
        if v.isdigit():
            return int(v)
        return None

    # ── Run helpers ───────────────────────────────────────────────────────

    def _guard(self):
        if self._running:
            self._log("⚠️  A scan is already running. Please wait.")
            return False
        return True

    def _run_in_thread(self, fn):
        self._running = True
        self._start_progress()
        threading.Thread(target=self._thread_wrapper(fn), daemon=True).start()

    def _thread_wrapper(self, fn):
        def wrapper():
            try:
                fn()
            except Exception as e:
                self.after(0, lambda: self._log(f"❌ Unexpected error: {e}"))
            finally:
                self._running = False
                self.after(0, self._stop_progress)
        return wrapper

    def _get_export_flags(self):
        return self.export_local_var.get(), self.export_sheets_var.get()

    # ── Action buttons ────────────────────────────────────────────────────

    def _run_clients(self):
        if not self._guard():
            return
        def job():
            path = self.clients_path.get()
            if not os.path.exists(path):
                self.after(0, lambda: self._log(f"❌ Path not found: {path}"))
                return
            self.after(0, lambda: self._log(f"📁 Scanning ALL CLIENTS ({path}) …"))
            records = process_directory(path, "", self._get_max(), self.deep_scan_var.get())
            self.after(0, lambda: self._log(f"   ✔ Found {len(records)} record groups"))
            loc, sht = self._get_export_flags()
            handle_upload(records, "clients_data", loc, sht, lambda m: self.after(0, lambda: self._log(m)))
        self._run_in_thread(job)

    def _run_consultants(self):
        if not self._guard():
            return
        def job():
            path = self.consultants_path.get()
            if not os.path.exists(path):
                self.after(0, lambda: self._log(f"❌ Path not found: {path}"))
                return
            self.after(0, lambda: self._log(f"📁 Scanning CONSULTANTS ({path}) …"))
            records = process_directory(path, "", self._get_max(), self.deep_scan_var.get())
            self.after(0, lambda: self._log(f"   ✔ Found {len(records)} record groups"))
            loc, sht = self._get_export_flags()
            handle_upload(records, "consultants_data", loc, sht, lambda m: self.after(0, lambda: self._log(m)))
        self._run_in_thread(job)

    def _run_both(self):
        if not self._guard():
            return
        def job():
            all_records = []
            for path, label, prefix in [
                (self.clients_path.get(),     "ALL CLIENTS",  "all_data"),
                (self.consultants_path.get(), "CONSULTANTS",  "all_data"),
            ]:
                if os.path.exists(path):
                    self.after(0, lambda l=label: self._log(f"📁 Scanning {l} …"))
                    r = process_directory(path, "", self._get_max(), self.deep_scan_var.get())
                    all_records.extend(r)
                    self.after(0, lambda n=len(r), l=label: self._log(f"   ✔ {n} groups from {l}"))
                else:
                    self.after(0, lambda p=path: self._log(f"❌ Not found: {p}"))
            loc, sht = self._get_export_flags()
            handle_upload(all_records, "all_data", loc, sht, lambda m: self.after(0, lambda: self._log(m)))
        self._run_in_thread(job)

    def _run_custom(self):
        if not self._guard():
            return
        def job():
            path = self.custom_path.get().strip()
            if not path:
                self.after(0, lambda: self._log("❌ Custom path is empty. Use Browse… to select a folder."))
                return
            if not os.path.exists(path):
                self.after(0, lambda: self._log(f"❌ Path not found: {path}"))
                return
            self.after(0, lambda: self._log(f"📂 Scanning custom path ({path}) …"))
            records = process_directory(path, "", self._get_max(), self.deep_scan_var.get())
            self.after(0, lambda: self._log(f"   ✔ Found {len(records)} record groups"))
            loc, sht = self._get_export_flags()
            handle_upload(records, "custom_data", loc, sht, lambda m: self.after(0, lambda: self._log(m)))
        self._run_in_thread(job)

    def _run_quick(self):
        """Quick export — fast 2-level scan, local files only, no pattern matching."""
        if not self._guard():
            return
        def job():
            all_records = []
            for path, label in [
                (self.clients_path.get(),     "ALL CLIENTS"),
                (self.consultants_path.get(), "CONSULTANTS"),
            ]:
                if os.path.exists(path):
                    self.after(0, lambda l=label: self._log(f"⚡ Quick scan {l} …"))
                    r = process_directory(path, "", None, deep_scan=False)
                    all_records.extend(r)
                    self.after(0, lambda n=len(r), l=label: self._log(f"   ✔ {n} from {l}"))
                else:
                    self.after(0, lambda p=path: self._log(f"❌ Not found: {p}"))

            if all_records:
                df = pd.DataFrame(all_records)
                base_cols = ["CLIENT NUMBER", "CLIENT NAME", "CASE #", "CASE NAME",
                             "TM NO", "CLASS", "FILES", "EXT", "DATE ADDED"]
                existing  = [c for c in base_cols if c in df.columns]
                df = df[existing]
                out_xlsx = os.path.join(EXPORT_DIR, "drive_data_export.xlsx")
                out_csv  = os.path.join(EXPORT_DIR, "drive_data_export.csv")
                df.to_excel(out_xlsx, index=False, engine='openpyxl')
                df.to_csv(out_csv, index=False)
                self.after(0, lambda: self._log(f"✅ Quick export done — {len(all_records)} records"))
                self.after(0, lambda: self._log(f"   📊 {out_xlsx}"))
            else:
                self.after(0, lambda: self._log("⚠️  No records found."))
        self._run_in_thread(job)

    # ── Colour utility ────────────────────────────────────────────────────

    @staticmethod
    def _darken(hex_color):
        r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        r, g, b = max(0, r - 30), max(0, g - 30), max(0, b - 30)
        return f"#{r:02x}{g:02x}{b:02x}"


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = DriveDataApp()
    app.mainloop()
