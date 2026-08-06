import os
import re
import json
import threading
import pandas as pd
from pathlib import Path
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

# ══════════════════════════════════════════════════════════════════════════════
#  APPEARANCE
# ══════════════════════════════════════════════════════════════════════════════
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ══════════════════════════════════════════════════════════════════════════════
#  NEO-BRUTALISM COLOUR PALETTE
# ══════════════════════════════════════════════════════════════════════════════
C = {
    "bg":      "#F0E8D0",   # Warm Cream – main background
    "bg_alt":  "#E8DFC7",   # Deep Cream – alternate / section bg
    "panel":   "#FAF6EE",   # Off-White – cards, inputs
    "black":   "#0C0C0C",   # Near-Black – borders, text, shadow
    "accent":  "#C94A00",   # Burnt Orange – CTA, active elements
    "teal":    "#0A6B52",   # Dark Teal – success, secondary action
    "teal_lt": "#0D9970",   # Bright Teal – links, hover highlights
    "yellow":  "#D4A800",   # Bold Yellow – warnings, stamps
    "dim":     "#888888",   # Muted – subtitles, captions
    "white":   "#FFFFFF",
}

# ══════════════════════════════════════════════════════════════════════════════
#  PATHS & CONFIG
# ══════════════════════════════════════════════════════════════════════════════
BASE_DIR   = Path(__file__).parent.resolve()
EXPORT_DIR = str(BASE_DIR / "export")
RULES_FILE = str(BASE_DIR / "custom_rules.json")
os.makedirs(EXPORT_DIR, exist_ok=True)

SHEET_ID   = "1yu27k_3Z6cCJmcnQI52z1dIC52Zi9ZxaKlo9wJiNFiQ"
SHEET_NAME = "List"
SCOPES     = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DEFAULT_CLIENTS_PATH     = r"F:\Br004\My Drive\1 ALL CLIENTS"
DEFAULT_CONSULTANTS_PATH = r"F:\Br004\My Drive\2 CONSULTANTS"

# ══════════════════════════════════════════════════════════════════════════════
#  DEFAULT PATTERN RULES  (14 rules — updated per user feedback)
# ══════════════════════════════════════════════════════════════════════════════

DEFAULT_PATTERNS = {
    "TM-1": [
        r"\bTM-1\b", r"\bTM1\b", r"\(TM-1\)", r"\[TM-1\]",
    ],
    "TM-48": [
        r"\bTM-48\b", r"\bTM48\b", r"\(TM-48\)", r"\[TM-48\]",
        r"UPDATED\s*\[TM-48\]", r"TM-48\s*-\s*COPY",
    ],
    "EXAM": [
        r"\bEXAMINATION\b", r"\bSHOWCASE\b", r"SHOWCASE\s*NOTICE",
        r"17\(2\)\(B\)", r"14\(3\)\(A\)", r"14\(1\)\(b\)",
        r"\bREPLY\b", r"REPLY\s*OF\s*NOTICE", r"MULTIPAL\s*REPLIES",
    ],
    "ACK": [
        r"\bACK\b", r"ACKNOWLEDGMENT", r"ACKNOLDGEMENT",
    ],
    "ACCEPTANCE": [
        r"\bACCEPTANCE\b", r"ACCEPTANCE\s*DONE", r"COMPLETE\s*FILE",
    ],
    "D-NOTE": [
        r"\bTM-11\b", r"\bTM11\b", r"IPO-PAKISTAN\s*__\s*TM\s*11",
        r"TM\s*11", r"DEMAND\s*NOTE",
    ],
    "TM-16": [r"\bTM-16\b", r"\bTM16\b", r"TM\s*16"],
    "TM-50": [r"\bTM-50\b", r"\bTM50\b", r"TM\s*50"],
    "TM-06": [
        r"IPO-PAKISTAN\s*__\s*TM\s*06",
        r"IPO-PAKISTAN\s*__\s*TM\s*\d{2}",
    ],
    # COMPANY — board resolutions + company-type doc keywords
    "COMPANY": [
        r"BOARD\s*OF\s*RESULOTION", r"BOARD\s*OF\s*RESOLUTION",
        r"\bPVT\s*LTD\b", r"\bPRIVATE\s*LIMITED\b",
        r"\bSMC\b", r"\bLIMITED\b",
    ],
    # NTN — ID/CNIC docs, data sheets (non-company context handled in logic)
    "NTN": [
        r"\bNTN\b", r"\bCNIC\b", r"\bNIC\b", r"\bPASSPORT\b",
        r"\bID\s*[BF]?\b", r"DATA\s*SHEET",
    ],
    # OPPO — opposition + legal notice merged here
    "OPPO": [
        r"WITHDRAWN\s*LETTER", r"\bOPPOSITION\b",
        r"GROUNDS\s*OF\s*OPPOSITION", r"\bOPPO\b",
        r"LEGAL\s*NOTICE", r"LEGAL\s*NOTIC\b",   # ← Legal Notice → OPPO
    ],
    "PUB": [
        r"\bPUBLICATION\b", r"JOURNAL\s*PUBLICATION",
        r"JOURNAL\s*CONVERT", r"Journal_\d+",
    ],
    "CERTIFICATE": [
        r"\bCERTIFICATE\b", r"CERTIFICATE\s*WITH\s*SIGN",
        r"ORIGINAL\s*CERTIFICATE", r"TRADE\s*MARK\s*CERTIFICATE",
        r"RENEWAL\s*CERTIFICATE",
    ],
}

# Keywords that identify company-type data sheets → COMPANY instead of NTN
_COMPANY_KW = [r"\bPVT\b", r"\bPRIVATE\b", r"PVT\s*LTD", r"\bLIMITED\b",
               r"\bLTD\b", r"\bSMC\b", r"\bINC\b", r"\bCORPORATION\b"]

# Base column order for exports
BASE_COLUMNS = [
    "CLIENT NUMBER", "CLIENT NAME", "CASE #", "CASE NAME", "TM NO", "CLASS",
    "FILES", "EXT",
    "TM-1", "TM-48", "EXAM", "ACK", "ACCEPTANCE", "D-NOTE",
    "TM-16", "TM-50", "TM-06", "COMPANY", "NTN", "OPPO", "PUB", "CERTIFICATE",
    "DATE ADDED",
]

# ══════════════════════════════════════════════════════════════════════════════
#  CUSTOM RULES — persistence
# ══════════════════════════════════════════════════════════════════════════════

def load_custom_rules() -> list:
    if not os.path.exists(RULES_FILE):
        # Seed default patterns
        rules = []
        for name, pats in DEFAULT_PATTERNS.items():
            rules.append({"name": name, "patterns": pats, "target": name})
        save_custom_rules(rules)
        return rules
    try:
        with open(RULES_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        pass
    return []


def save_custom_rules(rules: list) -> None:
    with open(RULES_FILE, "w", encoding="utf-8") as fh:
        json.dump(rules, fh, indent=2, ensure_ascii=False)


def get_active_patterns() -> dict:
    patterns = {}
    for rule in load_custom_rules():
        name = rule.get("name", "").strip()
        pats = rule.get("patterns", [])
        if name and pats:
            patterns.setdefault(name, []).extend(pats)
    return patterns


def get_all_columns() -> list:
    cols = [
        "CLIENT NUMBER", "CLIENT NAME", "CASE #", "CASE NAME", "TM NO", "CLASS",
        "FILES", "EXT"
    ]
    for rule in load_custom_rules():
        name = rule.get("name", "").strip()
        if name and name not in cols:
            cols.append(name)
    cols.append("DATE ADDED")
    return cols


# ══════════════════════════════════════════════════════════════════════════════
#  FOLDER PARSING
# ══════════════════════════════════════════════════════════════════════════════

def parse_client_folder(name: str):
    m = re.match(r"^([A-Z]-\d+)\s+(.+)$", name)
    return (m.group(1), m.group(2)) if m else ("", name)


def parse_case_folder(name: str):
    parts = name.split()
    case_no = case_name = tm_no = cls = ""
    for p in parts:
        if re.match(r"^[A-Z]\d{3}-\d{3}$", p):            case_no = p
        elif case_no and not case_name and re.match(r"^[A-Z][a-zA-Z]+$", p):
            case_name = p
        elif re.match(r"^\d{6}$", p):                      tm_no = p
        elif re.match(r"^C\d+$", p):                       cls = p
    return case_no, case_name, tm_no, cls


def extract_full_case_name(folder: str, tm_no: str) -> str:
    if not tm_no or not re.search(rf"\b{tm_no}\b", folder):
        return ""
    parts = folder.split()
    out, found = [], False
    for p in parts:
        if re.match(r"^[A-Z]\d{3}-\d{3}$", p):   found = True;  continue
        if found:
            if p == tm_no:                          break
            if not re.match(r"^C\d+$", p):         out.append(p)
    return " ".join(out)


# ══════════════════════════════════════════════════════════════════════════════
#  PATTERN MATCHING
# ══════════════════════════════════════════════════════════════════════════════

def check_file_patterns(file_names: str) -> dict:
    file_list  = file_names.split("\n") if file_names else []
    all_text   = " ".join(file_list)
    patterns   = get_active_patterns()

    def _hit(pats):
        return any(re.search(p, all_text, re.IGNORECASE) for p in pats)

    results = {cat: (True if _hit(pats) else False) for cat, pats in patterns.items()}

    # Special logic: DATA SHEET + company keyword → COMPANY (clear NTN if only from data sheet)
    has_ds = bool(re.search(r"DATA\s*SHEET", all_text, re.IGNORECASE))
    has_co_kw = any(re.search(p, all_text, re.IGNORECASE) for p in _COMPANY_KW)
    pure_ntn_pats = [r"\bNTN\b", r"\bCNIC\b", r"\bNIC\b", r"\bPASSPORT\b", r"\bID\s*[BF]?\b"]

    if has_ds and has_co_kw:
        results["COMPANY"] = True
        if not any(re.search(p, all_text, re.IGNORECASE) for p in pure_ntn_pats):
            results["NTN"] = False

    return results


# ══════════════════════════════════════════════════════════════════════════════
#  DIRECTORY PROCESSING
# ══════════════════════════════════════════════════════════════════════════════

def _collect_files(file_list):
    out = []
    for f in file_list:
        if f.lower() == "desktop.ini":
            continue
        name, ext = os.path.splitext(f)
        if ext.lower() == ".ini":
            ext = ""
        out.append(f"{name}|{ext.lstrip('.')}")
    return out


def process_directory(base_path, _prefix, max_records=None, deep_scan=True):
    """Scan base_path and return list of record dicts."""
    case_groups = {}
    count = 0

    if deep_scan:
        for root, _dirs, files in os.walk(base_path):
            if max_records and count >= max_records:
                break
            if not files:
                continue
            rel   = os.path.relpath(root, base_path)
            comps = [] if rel == "." else rel.split(os.sep)
            cf    = comps[0] if comps else ""
            ff    = comps[1] if len(comps) > 1 else ""
            cn, cln = parse_client_folder(cf) if cf else ("", "Root/Uncategorized")
            no, nm, tm, cls = parse_case_folder(ff) if ff else ("", "—", "", "")
            if tm and ff:
                full = extract_full_case_name(ff, tm)
                if full:
                    nm = full
            key = (cn, cln, no, nm, tm, cls)
            vf  = _collect_files(files)
            if vf:
                if key not in case_groups:
                    case_groups[key] = []
                    count += 1
                case_groups[key].extend(vf)
    else:
        for cf in os.listdir(base_path):
            if max_records and count >= max_records:
                break
            cp = os.path.join(base_path, cf)
            if not os.path.isdir(cp):
                continue
            cn, cln = parse_client_folder(cf)
            for ff in os.listdir(cp):
                if max_records and count >= max_records:
                    break
                fp = os.path.join(cp, ff)
                if not os.path.isdir(fp):
                    continue
                no, nm, tm, cls = parse_case_folder(ff)
                full = extract_full_case_name(ff, tm)
                if full:
                    nm = full
                key = (cn, cln, no, nm, tm, cls)
                vf  = _collect_files(os.listdir(fp))
                if key not in case_groups:
                    case_groups[key] = []
                    count += 1
                case_groups[key].extend(vf)

    records = []
    for (cn, cln, no, nm, tm, cls), files in case_groups.items():
        fnames = "\n".join(f.split("|")[0] for f in files if f.split("|")[0])
        fexts  = "\n".join(f.split("|")[1] for f in files if f.split("|")[1])
        rec = {
            "CLIENT NUMBER": cn,   "CLIENT NAME": cln,
            "CASE #":        no,   "CASE NAME":   nm,
            "TM NO":         tm,   "CLASS":        cls,
            "FILES":         fnames, "EXT":        fexts,
            "DATE ADDED":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        rec.update(check_file_patterns(fnames))
        records.append(rec)
    return records


# ══════════════════════════════════════════════════════════════════════════════
#  GOOGLE SHEETS
# ══════════════════════════════════════════════════════════════════════════════

_HEADER_EMOJI = {
    "CLIENT NUMBER": "📋", "CLIENT NAME": "👤", "CASE #": "📁",
    "CASE NAME": "📝", "TM NO": "🔢", "CLASS": "📚",
    "FILES": "📎", "EXT": "📄", "TM-1": "📄", "TM-48": "📄",
    "EXAM": "📝", "ACK": "✅", "ACCEPTANCE": "✅", "D-NOTE": "📋",
    "TM-16": "📄", "TM-50": "📄", "TM-06": "📄",
    "COMPANY": "🏢", "NTN": "🪪", "OPPO": "⚖️",
    "PUB": "📰", "CERTIFICATE": "📜", "DATE ADDED": "📅",
}


def get_gs_client():
    cp = str(BASE_DIR / "credentials.json")
    if not os.path.exists(cp):
        return None, f"❌ credentials.json not found at {cp}"
    try:
        creds = Credentials.from_service_account_file(cp, scopes=SCOPES)
        return gspread.authorize(creds), None
    except Exception as exc:
        return None, str(exc)


def upload_to_sheets(records, log_fn=print):
    client, err = get_gs_client()
    if err:
        log_fn(err)
        return False
    try:
        sh   = client.open_by_key(SHEET_ID)
        cols = get_all_columns()
        hdrs = [f"{_HEADER_EMOJI.get(c, '🔹')} {c}" for c in cols]
        try:
            ws = sh.worksheet(SHEET_NAME)
            # Sync headers if they mismatch
            existing_hdrs = ws.row_values(1)
            if existing_hdrs != hdrs:
                log_fn("🔄 Sheet headers mismatch. Synchronizing headers...")
                if ws.col_count < len(hdrs):
                    ws.add_cols(len(hdrs) - ws.col_count)
                end_col = chr(64 + len(hdrs)) if len(hdrs) <= 26 else "A" + chr(64 + len(hdrs) - 26)
                ws.update(values=[hdrs], range_name=f"A1:{end_col}1")
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(SHEET_NAME, rows=2000, cols=len(hdrs))
            end_col = chr(64 + len(hdrs)) if len(hdrs) <= 26 else "A" + chr(64 + len(hdrs) - 26)
            ws.update(values=[hdrs], range_name=f"A1:{end_col}1")

        # Formatting: Bold headers, freeze first row, auto-resize columns
        try:
            sh.batch_update({
                "requests": [
                    {
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId": ws.id,
                                "gridProperties": {
                                    "frozenRowCount": 1
                                }
                            },
                            "fields": "gridProperties.frozenRowCount"
                        }
                    },
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": ws.id,
                                "startRowIndex": 0,
                                "endRowIndex": 1,
                                "startColumnIndex": 0,
                                "endColumnIndex": len(hdrs)
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "backgroundColor": {
                                        "red": 0.98,
                                        "green": 0.96,
                                        "blue": 0.93
                                    },
                                    "textFormat": {
                                        "bold": True,
                                        "fontSize": 10,
                                        "fontFamily": "Arial"
                                    },
                                    "borders": {
                                        "bottom": {
                                            "style": "SOLID_MEDIUM",
                                            "color": {"red": 0.12, "green": 0.12, "blue": 0.12}
                                        }
                                    }
                                }
                            },
                            "fields": "userEnteredFormat(backgroundColor,textFormat,borders)"
                        }
                    },
                    {
                        "autoResizeDimensions": {
                            "dimensions": {
                                "sheetId": ws.id,
                                "dimension": "COLUMNS",
                                "startIndex": 0,
                                "endIndex": len(hdrs)
                            }
                        }
                    }
                ]
            })
        except Exception as fmt_err:
            log_fn(f"⚠️ Formatting warning: {fmt_err}")

        data = [[r.get(c, "") for c in cols] for r in records]
        ws.append_rows(data)
        log_fn(f"✅ Uploaded {len(records)} records to Google Sheets")
        return True
    except Exception as exc:
        log_fn(f"❌ Sheets error: {exc}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  LOCAL EXPORT
# ══════════════════════════════════════════════════════════════════════════════

_SHORT = {
    "consultants_data": "cons_patterns",
    "clients_data":     "clients_patterns",
    "all_data":         "all_patterns",
    "custom_data":      "custom_patterns",
}


def get_unique_filepath(base_dir, name, ext):
    path = os.path.join(base_dir, f"{name}.{ext}")
    if not os.path.exists(path):
        return path
    idx = 1
    while True:
        path = os.path.join(base_dir, f"{name}_{idx}.{ext}")
        if not os.path.exists(path):
            return path
        idx += 1


def export_local(records, prefix, log_fn=print):
    if not records:
        log_fn("No records!")
        return
    df   = pd.DataFrame(records)
    cols = [c for c in get_all_columns() if c in df.columns]
    df   = df[cols]
    short = _SHORT.get(prefix, prefix)
    xlsx  = get_unique_filepath(EXPORT_DIR, short, "xlsx")
    csv   = get_unique_filepath(EXPORT_DIR, short, "csv")
    df.to_excel(xlsx, index=False, engine="openpyxl")
    df.to_csv(csv, index=False)
    log_fn(f"💾 Exported {len(df)} records")
    log_fn(f"   📊 Excel → {xlsx}")
    log_fn(f"   📄 CSV   → {csv}")


def handle_upload(records, prefix, do_local, do_sheets, log_fn=print):
    if not records:
        log_fn("❌ No records found!")
        return
    if do_local:
        export_local(records, prefix, log_fn)
    if do_sheets:
        upload_to_sheets(records, log_fn)


# ══════════════════════════════════════════════════════════════════════════════
#  GUI HELPER WIDGETS
# ══════════════════════════════════════════════════════════════════════════════

def _shadow_card(master, fg=None, shadow=5, **grid_kw):
    """Returns a frame styled as a Neo-Brutalist hard-shadow card."""
    wrapper = ctk.CTkFrame(master, fg_color=C["black"], corner_radius=0)
    wrapper.grid(**grid_kw)
    inner = ctk.CTkFrame(wrapper, fg_color=fg or C["panel"],
                          corner_radius=0, border_width=2, border_color=C["black"])
    inner.pack(padx=(0, shadow), pady=(0, shadow), fill="both", expand=True)
    return inner


def _nb_btn(master, text, cmd, fg=None, tc=None, **grid_kw):
    """Neo-Brutalist button."""
    btn = ctk.CTkButton(
        master, text=text, command=cmd,
        fg_color=fg or C["accent"],
        hover_color=C["teal"],
        text_color=tc or C["white"],
        font=ctk.CTkFont(family="Arial Black", size=12, weight="bold"),
        corner_radius=0, border_width=2, border_color=C["black"], height=40,
    )
    btn.grid(**grid_kw)
    return btn


def _nb_label(master, text, size=12, weight="bold", color=None, **grid_kw):
    lbl = ctk.CTkLabel(
        master, text=text,
        font=ctk.CTkFont(family="Arial Black", size=size, weight=weight),
        text_color=color or C["black"],
    )
    lbl.grid(**grid_kw)
    return lbl


def _nb_entry(master, var=None, ph="", width=200, **grid_kw):
    e = ctk.CTkEntry(
        master, textvariable=var, placeholder_text=ph,
        fg_color=C["panel"], border_color=C["black"], border_width=2,
        corner_radius=0, text_color=C["black"],
        font=ctk.CTkFont(family="Arial", size=12), width=width,
    )
    e.grid(**grid_kw)
    return e


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

class DriveDataApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DRIVE DATA — PATTERN MATCHER")
        self.geometry("1000x820")
        self.minsize(860, 700)
        self.configure(fg_color=C["bg"])

        # Check Google Connection
        client, err = get_gs_client()
        self.google_connected = (err is None)

        # State
        self._running      = False
        self._editing_rule = None
        self.clients_path  = ctk.StringVar(value=DEFAULT_CLIENTS_PATH)
        self.conslt_path   = ctk.StringVar(value=DEFAULT_CONSULTANTS_PATH)
        self.custom_path   = ctk.StringVar(value="")
        self.max_rec_var   = ctk.StringVar(value="")
        self.deep_scan_var = ctk.BooleanVar(value=True)
        self.loc_var       = ctk.BooleanVar(value=True)
        self.sht_var       = ctk.BooleanVar(value=True)

        self._tab_btns  = {}
        self._tab_pages = {}
        self._build_ui()

    # ─── UI Construction ─────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Sticky dark header ─────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=C["black"], corner_radius=0, height=58)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr, text="🗂  DRIVE DATA — PATTERN MATCHER",
            font=ctk.CTkFont(family="Arial Black", size=19, weight="bold"),
            text_color=C["panel"],
        ).grid(row=0, column=0, sticky="w", padx=20, pady=0)

        # Google status indicator
        g_color = C["teal"] if self.google_connected else C["accent"]
        g_lbl = "CONNECTED" if self.google_connected else "DISCONNECTED"
        g_frame = ctk.CTkFrame(hdr, fg_color=g_color, corner_radius=0)
        g_frame.grid(row=0, column=1, padx=(0, 8))
        ctk.CTkLabel(
            g_frame,
            text=f"  GOOGLE: {g_lbl}  ",
            font=ctk.CTkFont(family="Arial Black", size=10, weight="bold"),
            text_color=C["white"],
        ).pack(padx=2, pady=6)

        badge_frame = ctk.CTkFrame(hdr, fg_color=C["black"], border_color=C["panel"], border_width=1, corner_radius=0)
        badge_frame.grid(row=0, column=2, padx=(0, 16))
        ctk.CTkLabel(
            badge_frame,
            text=f"  v2.0 · {len(get_active_patterns())} RULES  ",
            font=ctk.CTkFont(family="Arial Black", size=10, weight="bold"),
            text_color=C["panel"],
        ).pack(padx=2, pady=6)

        # ── Tab bar ────────────────────────────────────────────────────────
        tab_bar = ctk.CTkFrame(self, fg_color=C["bg_alt"], corner_radius=0, height=40)
        tab_bar.grid(row=1, column=0, sticky="ew")
        tab_bar.grid_propagate(False)

        tabs = [
            ("scan",     "📁  SCAN"),
            ("rules",    "⚙  RULES MANAGER"),
            ("about",    "ℹ  ABOUT"),
        ]
        for i, (key, lbl) in enumerate(tabs):
            btn = ctk.CTkButton(
                tab_bar, text=lbl, height=40, width=190,
                fg_color=C["accent"], text_color=C["white"],
                hover_color=C["teal_lt"],
                font=ctk.CTkFont(family="Arial Black", size=11, weight="bold"),
                corner_radius=0, border_width=0,
                command=lambda k=key: self._switch_tab(k),
            )
            btn.place(x=i * 192, y=0)
            self._tab_btns[key] = btn

        # ── Content container ──────────────────────────────────────────────
        content = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        content.grid(row=2, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)

        for key, build_fn in [
            ("scan",  self._build_scan),
            ("rules", self._build_rules),
            ("about", self._build_about),
        ]:
            page = ctk.CTkFrame(content, fg_color=C["bg"], corner_radius=0)
            page.grid(row=0, column=0, sticky="nsew")
            page.grid_columnconfigure(0, weight=1)
            page.grid_rowconfigure(0, weight=1)
            self._tab_pages[key] = page
            build_fn(page)

        self._switch_tab("scan")

    def _switch_tab(self, key):
        self._tab_pages[key].tkraise()
        for k, btn in self._tab_btns.items():
            btn.configure(
                fg_color=C["accent"] if k == key else C["bg_alt"],
                text_color=C["white"] if k == key else C["black"],
            )

    # ─── SCAN TAB ────────────────────────────────────────────────────────────

    def _build_scan(self, parent):
        parent.grid_rowconfigure(4, weight=1)

        # Path config
        cfg = _shadow_card(parent, shadow=5,
                           row=0, column=0, sticky="ew", padx=18, pady=(18, 6))
        cfg.grid_columnconfigure(1, weight=1)
        _nb_label(cfg, "PATH CONFIGURATION", size=10, weight="normal",
                  color=C["dim"], row=0, column=0, columnspan=3, sticky="w",
                  padx=14, pady=(10, 2))
        self._path_row(cfg, "ALL CLIENTS :", self.clients_path, 1, self._browse_clients)
        self._path_row(cfg, "CONSULTANTS :", self.conslt_path,  2, self._browse_conslt)
        self._path_row(cfg, "CUSTOM PATH :", self.custom_path,  3, self._browse_custom)

        # Options
        opts = _shadow_card(parent, fg=C["bg_alt"], shadow=4,
                            row=1, column=0, sticky="ew", padx=18, pady=4)
        opts.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        _nb_label(opts, "MAX RECORDS:", size=10, weight="normal",
                  row=0, column=0, padx=(14, 4), pady=10, sticky="e")
        _nb_entry(opts, var=self.max_rec_var, ph="ALL",
                  width=80, row=0, column=1, pady=10, sticky="w")

        ctk.CTkSwitch(
            opts, text="DEEP SCAN", variable=self.deep_scan_var,
            font=ctk.CTkFont(family="Arial Black", size=11, weight="bold"),
            button_color=C["accent"], progress_color=C["teal"], text_color=C["black"],
        ).grid(row=0, column=2, padx=16)

        for col, (lbl, var) in enumerate(
            [("💾 LOCAL", self.loc_var), ("🌐 SHEETS", self.sht_var)], start=3
        ):
            ctk.CTkCheckBox(
                opts, text=lbl, variable=var,
                font=ctk.CTkFont(family="Arial Black", size=11, weight="bold"),
                fg_color=C["accent"], hover_color=C["teal"],
                border_color=C["black"], text_color=C["black"],
                checkmark_color=C["white"], corner_radius=0,
            ).grid(row=0, column=col, padx=12)

        # Action buttons
        btns = _shadow_card(parent, fg=C["bg_alt"], shadow=4,
                            row=2, column=0, sticky="ew", padx=18, pady=4)
        btns.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        specs = [
            ("👥 ALL CLIENTS",  C["black"],   C["white"], self._run_clients),
            ("🤝 CONSULTANTS",  C["teal"],    C["white"], self._run_conslt),
            ("📦 BOTH",         C["teal"],    C["white"], self._run_both),
            ("📂 CUSTOM",       C["accent"],  C["white"], self._run_custom),
            ("⚡ QUICK EXPORT", C["yellow"],  C["black"], self._run_quick),
        ]
        for col, (lbl, fg, tc, cmd) in enumerate(specs):
            _nb_btn(btns, lbl, cmd, fg=fg, tc=tc,
                    row=0, column=col, padx=8, pady=10, sticky="ew")

        # Progress bar
        self.progress = ctk.CTkProgressBar(
            parent, height=6,
            fg_color=C["bg_alt"], progress_color=C["accent"], corner_radius=0,
        )
        self.progress.grid(row=3, column=0, sticky="ew", padx=18, pady=(2, 0))
        self.progress.set(0)

        # Log console
        log_card = _shadow_card(parent, fg=C["black"], shadow=5,
                                row=4, column=0, sticky="nsew",
                                padx=18, pady=(6, 18))
        log_card.grid_rowconfigure(1, weight=1)
        log_card.grid_columnconfigure(0, weight=1)

        log_hdr = ctk.CTkFrame(log_card, fg_color="transparent")
        log_hdr.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 0))
        log_hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            log_hdr, text="STATUS LOG",
            font=ctk.CTkFont(family="Arial Black", size=11, weight="bold"),
            text_color=C["teal_lt"],
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            log_hdr, text="CLEAR", width=64, height=24,
            fg_color=C["accent"], hover_color=C["teal"],
            corner_radius=0, border_width=1, border_color=C["white"],
            font=ctk.CTkFont(family="Arial", size=10, weight="bold"),
            text_color=C["white"], command=self._clear_log,
        ).grid(row=0, column=1)

        self.log_box = ctk.CTkTextbox(
            log_card,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=C["black"], text_color=C["teal_lt"],
            corner_radius=0, wrap="word", state="disabled",
        )
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4, 10))

        self._log("▶  DRIVE DATA PATTERN MATCHER v2.0 — Ready")
        self._log(f"   {len(get_active_patterns())} active rules · {len(get_all_columns())} export columns")

    def _path_row(self, parent, label, var, row, browse_cmd):
        ctk.CTkLabel(
            parent, text=label,
            font=ctk.CTkFont(family="Arial Black", size=11, weight="bold"),
            text_color=C["black"], width=130, anchor="e",
        ).grid(row=row, column=0, padx=(14, 6), pady=4, sticky="e")

        ctk.CTkEntry(
            parent, textvariable=var,
            fg_color=C["panel"], border_color=C["black"], border_width=2,
            corner_radius=0, text_color=C["black"],
            font=ctk.CTkFont(family="Arial", size=11),
        ).grid(row=row, column=1, padx=4, pady=4, sticky="ew")

        ctk.CTkButton(
            parent, text="BROWSE…", width=90, height=28,
            fg_color=C["bg_alt"], hover_color=C["teal_lt"],
            text_color=C["black"], corner_radius=0,
            border_width=2, border_color=C["black"],
            font=ctk.CTkFont(family="Arial Black", size=10, weight="bold"),
            command=browse_cmd,
        ).grid(row=row, column=2, padx=(4, 14), pady=4)

    # ─── RULES MANAGER TAB ───────────────────────────────────────────────────

    def _build_rules(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        _nb_label(parent, "⚙  RULES MANAGER", size=15,
                  row=0, column=0, sticky="w", padx=20, pady=(16, 4))

        pane = ctk.CTkFrame(parent, fg_color=C["bg"], corner_radius=0)
        pane.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        pane.grid_rowconfigure(0, weight=1)
        pane.grid_columnconfigure((0, 1), weight=1)

        # ── Left: rule list ────────────────────────────────────────────────
        left = _shadow_card(pane, shadow=5,
                            row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        _nb_label(left, "ACTIVE RULES", size=10, weight="normal", color=C["dim"],
                  row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        self.rules_scroll = ctk.CTkScrollableFrame(left, fg_color=C["panel"],
                                                    corner_radius=0)
        self.rules_scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.rules_scroll.grid_columnconfigure(0, weight=1)

        # ── Right: add rule form ───────────────────────────────────────────
        right = _shadow_card(pane, shadow=5,
                             row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)
        right.grid_columnconfigure(0, weight=1)

        _nb_label(right, "ADD CUSTOM RULE", size=10, weight="normal", color=C["dim"],
                  row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        self._r_name = ctk.StringVar()
        self._r_tgt  = ctk.StringVar()

        _nb_label(right, "RULE / COLUMN NAME:", size=10, weight="normal",
                  row=1, column=0, sticky="w", padx=12, pady=(8, 0))
        _nb_entry(right, var=self._r_name, ph="e.g. MY RULE",
                  width=240, row=2, column=0, sticky="ew", padx=12, pady=2)

        _nb_label(right, "PATTERNS (one per line, regex ok):", size=10, weight="normal",
                  row=3, column=0, sticky="w", padx=12, pady=(8, 0))
        self._r_pats = ctk.CTkTextbox(
            right, height=100,
            fg_color=C["panel"], border_color=C["black"], border_width=2,
            corner_radius=0, text_color=C["black"],
            font=ctk.CTkFont(family="Consolas", size=11),
        )
        self._r_pats.grid(row=4, column=0, sticky="ew", padx=12, pady=2)

        _nb_label(right, "MERGE INTO EXISTING COLUMN (optional):", size=10, weight="normal",
                  row=5, column=0, sticky="w", padx=12, pady=(8, 0))
        _nb_entry(right, var=self._r_tgt, ph="e.g. OPPO  (blank = create new)",
                  width=240, row=6, column=0, sticky="ew", padx=12, pady=2)

        self.btn_save = _nb_btn(right, "➕  SAVE RULE", self._save_rule, fg=C["teal"],
                                row=7, column=0, sticky="ew", padx=12, pady=(14, 4))
        _nb_btn(right, "🔄  RELOAD LIST", self._reload_rules, fg=C["black"],
                row=8, column=0, sticky="ew", padx=12, pady=4)

        tip = ("ℹ  Tip: patterns use Python regex. Leave TARGET blank\n"
               "to create a new column. Match to an existing column\n"
               "name (e.g. OPPO) to extend it.")
        ctk.CTkLabel(
            right, text=tip, justify="left",
            font=ctk.CTkFont(family="Arial", size=10),
            text_color=C["dim"],
        ).grid(row=9, column=0, sticky="w", padx=12, pady=(8, 0))

        self._refresh_rules_list()

    def _refresh_rules_list(self):
        for w in self.rules_scroll.winfo_children():
            w.destroy()

        row = 0
        # All rules are now custom/editable
        for rule in load_custom_rules():
            n   = rule.get("name", "?")
            p   = rule.get("patterns", [])
            tgt = rule.get("target", n)
            self._rule_row(n, f"{len(p)} pattern(s)  →  {tgt}", row,
                           is_custom=True, rule_data=rule)
            row += 1

    def _rule_row(self, name, subtitle, row, is_custom=False, rule_data=None):
        bg = "#FFF8E6" if is_custom else C["panel"]
        f  = ctk.CTkFrame(self.rules_scroll, fg_color=bg, corner_radius=0,
                           border_width=1, border_color=C["black"])
        f.grid(row=row, column=0, sticky="ew", pady=2, padx=2)
        f.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            f, text=name,
            font=ctk.CTkFont(family="Arial Black", size=11, weight="bold"),
            text_color=C["accent"] if is_custom else C["black"],
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(4, 0))

        ctk.CTkLabel(
            f, text=subtitle,
            font=ctk.CTkFont(family="Arial", size=10),
            text_color=C["dim"],
        ).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 4))

        if is_custom and rule_data:
            # Edit button (pencil)
            ctk.CTkButton(
                f, text="✎", width=28, height=28,
                fg_color=C["teal"], hover_color=C["teal_lt"],
                corner_radius=0, font=ctk.CTkFont(size=12),
                text_color=C["white"],
                command=lambda rd=rule_data: self._edit_rule(rd),
            ).grid(row=0, column=1, rowspan=2, padx=(4, 2), pady=4)

            # Delete button (cross)
            ctk.CTkButton(
                f, text="✕", width=28, height=28,
                fg_color=C["accent"], hover_color="#8B0000",
                corner_radius=0, font=ctk.CTkFont(size=12),
                text_color=C["white"],
                command=lambda rd=rule_data: self._delete_rule(rd),
            ).grid(row=0, column=2, rowspan=2, padx=(2, 8), pady=4)

    def _edit_rule(self, rule_data):
        self._editing_rule = rule_data
        self._r_name.set(rule_data.get("name", ""))
        self._r_tgt.set(rule_data.get("target", ""))
        self._r_pats.delete("1.0", "end")
        self._r_pats.insert("1.0", "\n".join(rule_data.get("patterns", [])))
        self.btn_save.configure(text="💾  UPDATE RULE")
        self._log(f"📝  Editing rule '{rule_data.get('name')}'")

    def _save_rule(self):
        name = self._r_name.get().strip().upper()
        raw  = self._r_pats.get("1.0", "end").strip()
        tgt  = self._r_tgt.get().strip().upper() or name

        if not name or not raw:
            messagebox.showwarning("Missing fields",
                                   "Rule name and at least one pattern are required.")
            return

        pats  = [p.strip() for p in raw.splitlines() if p.strip()]
        rules = load_custom_rules()

        if self._editing_rule is not None:
            # Update existing rule
            for idx, r in enumerate(rules):
                if r == self._editing_rule:
                    rules[idx] = {"name": name, "patterns": pats, "target": tgt}
                    break
            self._editing_rule = None
            self.btn_save.configure(text="➕  SAVE RULE")
            self._log(f"✅ Custom rule '{name}' updated ({len(pats)} pattern(s)) → column '{tgt}'")
        else:
            # Create new rule
            rules.append({"name": name, "patterns": pats, "target": tgt})
            self._log(f"✅ Custom rule '{name}' saved ({len(pats)} pattern(s)) → column '{tgt}'")

        save_custom_rules(rules)
        self._r_name.set("")
        self._r_pats.delete("1.0", "end")
        self._r_tgt.set("")
        self._refresh_rules_list()

    def _delete_rule(self, rule_data):
        if self._editing_rule == rule_data:
            self._editing_rule = None
            self.btn_save.configure(text="➕  SAVE RULE")
            self._r_name.set("")
            self._r_pats.delete("1.0", "end")
            self._r_tgt.set("")
        rules = [r for r in load_custom_rules() if r != rule_data]
        save_custom_rules(rules)
        self._refresh_rules_list()
        self._log(f"🗑  Deleted rule '{rule_data.get('name', '')}'")

    def _reload_rules(self):
        self._refresh_rules_list()
        n = len(get_active_patterns())
        self._log(f"🔄 Rules reloaded — {n} active")

    # ─── ABOUT TAB ────────────────────────────────────────────────────────────

    def _build_about(self, parent):
        card = _shadow_card(parent, shadow=6,
                            row=0, column=0, sticky="nsew", padx=40, pady=30)
        card.grid_columnconfigure(0, weight=1)

        texts = [
            ("DRIVE DATA — PATTERN MATCHER", 20, C["black"]),
            ("Version 2.0  ·  Neo-Brutalism Edition", 13, C["dim"]),
            ("", 10, C["dim"]),
            ("Scans Google Drive folder structures mounted locally,", 12, C["black"]),
            ("classifies trademark case files using 14+ regex rules,", 12, C["black"]),
            ("and exports to Excel, CSV, or Google Sheets.", 12, C["black"]),
            ("", 10, C["dim"]),
            ("AUTHOR", 11, C["accent"]),
            ("Nadeem (OutLawZ)  ·  Brandex Trademark Services", 12, C["black"]),
            ("net2outlawzz@gmail.com  ·  brandex.pk", 12, C["teal"]),
            ("", 10, C["dim"]),
            ("RULES FILE", 11, C["accent"]),
            (str(RULES_FILE), 11, C["dim"]),
            ("EXPORT DIR", 11, C["accent"]),
            (str(EXPORT_DIR), 11, C["dim"]),
        ]

        for i, (text, size, color) in enumerate(texts):
            ctk.CTkLabel(
                card, text=text,
                font=ctk.CTkFont(family="Arial Black" if size >= 13 else "Arial",
                                 size=size, weight="bold" if size >= 13 else "normal"),
                text_color=color,
            ).grid(row=i, column=0, sticky="w", padx=20, pady=(2 if text else 0, 0))

    # ─── Run helpers ──────────────────────────────────────────────────────────

    def _browse_clients(self):
        p = filedialog.askdirectory(title="Select ALL CLIENTS folder")
        if p: self.clients_path.set(p)

    def _browse_conslt(self):
        p = filedialog.askdirectory(title="Select CONSULTANTS folder")
        if p: self.conslt_path.set(p)

    def _browse_custom(self):
        p = filedialog.askdirectory(title="Select custom folder")
        if p: self.custom_path.set(p)

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{ts}]  {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _start_prog(self):
        self.progress.configure(mode="indeterminate")
        self.progress.start()

    def _stop_prog(self):
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress.set(1)

    def _get_max(self):
        v = self.max_rec_var.get().strip()
        return int(v) if v.isdigit() else None

    def _guard(self):
        if self._running:
            self._log("⚠  Already scanning — please wait.")
            return False
        return True

    def _show_popup(self, title, message):
        # Create popup window styled as Neo-Brutalist
        popup = ctk.CTkToplevel(self)
        popup.title(title)
        popup.geometry("380x200")
        popup.configure(fg_color=C["bg"])
        popup.transient(self)
        popup.grab_set()

        popup.update_idletasks()
        w = popup.winfo_width()
        h = popup.winfo_height()
        extra_x = (self.winfo_width() - w) // 2
        extra_y = (self.winfo_height() - h) // 2
        popup.geometry(f"+{self.winfo_x() + extra_x}+{self.winfo_y() + extra_y}")

        # Neo-Brutalist card layout
        card = _shadow_card(popup, shadow=5, row=0, column=0, sticky="nsew", padx=15, pady=15)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)
        popup.grid_columnconfigure(0, weight=1)
        popup.grid_rowconfigure(0, weight=1)

        _nb_label(card, title.upper(), size=14, weight="bold", color=C["accent"], row=0, column=0, pady=(10, 5))

        lbl_msg = ctk.CTkLabel(
            card, text=message,
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            text_color=C["black"], justify="center", wraplength=300
        )
        lbl_msg.grid(row=1, column=0, pady=5, sticky="nsew")

        _nb_btn(card, "OK", popup.destroy, fg=C["black"], tc=C["white"], row=2, column=0, pady=(10, 10), padx=40, sticky="ew")

    def _wrap(self, fn, job_name="Scan Job"):
        def wrapper():
            try:
                records_count = fn()
                if records_count is not None:
                    self.after(0, lambda: self._show_popup("JOB DONE", f"{job_name} finished successfully!\nProcessed {records_count} records."))
            except Exception as exc:
                self.after(0, lambda: self._log(f"❌ Error: {exc}"))
                self.after(0, lambda: self._show_popup("ERROR", f"An error occurred:\n{exc}"))
            finally:
                self._running = False
                self.after(0, self._stop_prog)
        return wrapper

    def _post(self, msg):
        self.after(0, lambda m=msg: self._log(m))

    def _run_thread(self, fn, job_name="Scan Job"):
        self._running = True
        self._start_prog()
        threading.Thread(target=self._wrap(fn, job_name), daemon=True).start()

    def _flags(self):
        return self.loc_var.get(), self.sht_var.get()

    # ─── Scan actions ─────────────────────────────────────────────────────────

    def _run_clients(self):
        if not self._guard(): return
        def job():
            p = self.clients_path.get()
            if not os.path.exists(p): self._post(f"❌ Not found: {p}"); return 0
            self._post("📁 Scanning ALL CLIENTS …")
            recs = process_directory(p, "", self._get_max(), self.deep_scan_var.get())
            self._post(f"   ✔ {len(recs)} record groups found")
            handle_upload(recs, "clients_data", *self._flags(), self._post)
            return len(recs)
        self._run_thread(job, "All Clients Scan")

    def _run_conslt(self):
        if not self._guard(): return
        def job():
            p = self.conslt_path.get()
            if not os.path.exists(p): self._post(f"❌ Not found: {p}"); return 0
            self._post("🤝 Scanning CONSULTANTS …")
            recs = process_directory(p, "", self._get_max(), self.deep_scan_var.get())
            self._post(f"   ✔ {len(recs)} record groups found")
            handle_upload(recs, "consultants_data", *self._flags(), self._post)
            return len(recs)
        self._run_thread(job, "Consultants Scan")

    def _run_both(self):
        if not self._guard(): return
        def job():
            all_recs = []
            for path, label in [(self.clients_path.get(), "ALL CLIENTS"),
                                 (self.conslt_path.get(), "CONSULTANTS")]:
                if os.path.exists(path):
                    self._post(f"📦 Scanning {label} …")
                    r = process_directory(path, "", self._get_max(), self.deep_scan_var.get())
                    all_recs.extend(r)
                    self._post(f"   ✔ {len(r)} from {label}")
                else:
                    self._post(f"❌ Not found: {path}")
            handle_upload(all_recs, "all_data", *self._flags(), self._post)
            return len(all_recs)
        self._run_thread(job, "Scan Both Directories")

    def _run_custom(self):
        if not self._guard(): return
        def job():
            p = self.custom_path.get().strip()
            if not p:              self._post("❌ Custom path is empty."); return 0
            if not os.path.exists(p): self._post(f"❌ Not found: {p}"); return 0
            self._post(f"📂 Scanning: {p}")
            recs = process_directory(p, "", self._get_max(), self.deep_scan_var.get())
            self._post(f"   ✔ {len(recs)} record groups found")
            handle_upload(recs, "custom_data", *self._flags(), self._post)
            return len(recs)
        self._run_thread(job, "Custom Path Scan")

    def _run_quick(self):
        if not self._guard(): return
        def job():
            all_recs = []
            for path, label in [(self.clients_path.get(), "ALL CLIENTS"),
                                 (self.conslt_path.get(), "CONSULTANTS")]:
                if os.path.exists(path):
                    self._post(f"⚡ Quick scan {label} …")
                    r = process_directory(path, "", None, deep_scan=False)
                    all_recs.extend(r)
                    self._post(f"   ✔ {len(r)} groups")
                else:
                    self._post(f"❌ Not found: {path}")
            if all_recs:
                df = pd.DataFrame(all_recs)
                base = ["CLIENT NUMBER", "CLIENT NAME", "CASE #", "CASE NAME",
                        "TM NO", "CLASS", "FILES", "EXT", "DATE ADDED"]
                df = df[[c for c in base if c in df.columns]]
                xlsx = get_unique_filepath(EXPORT_DIR, "drive_data_export", "xlsx")
                csv  = get_unique_filepath(EXPORT_DIR, "drive_data_export", "csv")
                df.to_excel(xlsx, index=False, engine="openpyxl")
                df.to_csv(csv, index=False)
                self._post(f"✅ Quick export done — {len(all_recs)} records")
                self._post(f"   📊 {xlsx}")
            return len(all_recs)
        self._run_thread(job, "Quick Export Scan")


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = DriveDataApp()
    app.mainloop()
