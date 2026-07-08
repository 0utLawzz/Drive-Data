"""
scanner/parser.py — Folder name parsing for Data-Shaper V2.

Handles multiple real-world folder naming formats without crashing.
Missing fields silently return empty strings.

Supported case-folder formats
------------------------------
  A020-003 Trendy Toys 747478 C32
  A020-003 Trendy Toys 747478 Class 32
  A020-003 Trendy-Toys
  A020-003
  A-020-003 Trendy Toys
  X015-001 My Brand 555555 C5

Parsed fields
-------------
  case_no   — full token e.g. "A020-003" or "A-020-003"
  case_name — brand / trademark name between case_no and TM number
  tm_no     — 6-digit registration number
  class_code — normalised to "C<n>" form (e.g. "C32")
"""

import re

# ---------------------------------------------------------------------------
# Compiled patterns (compiled once at import time for performance)
# ---------------------------------------------------------------------------

# Client folder: "A-020 ClientName …"  or  "A-020"
_CLIENT_RE = re.compile(r'^([A-Z]-\d+)\s+(.+)$')
_CLIENT_CODE_ONLY_RE = re.compile(r'^([A-Z]-\d+)$')

# Case folder case-number token: A020-003 or A-020-003
_CASE_NO_RE = re.compile(r'^[A-Z]-?\d{2,4}-\d{2,4}$')

# 6-digit TM registration number
_TM_NO_RE = re.compile(r'^\d{6}$')

# Class code: C32, C5, c32 …
_CLASS_CODE_RE = re.compile(r'^C\d+$', re.IGNORECASE)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_client_folder(folder_name: str) -> tuple[str, str]:
    """
    Extract (client_number, client_name) from a client folder name.

    Examples
    --------
    "A-020 Brandex International"  →  ("A-020", "Brandex International")
    "B-005"                        →  ("B-005", "")
    "random folder"                →  ("", "random folder")
    """
    folder_name = folder_name.strip()

    m = _CLIENT_RE.match(folder_name)
    if m:
        return m.group(1), m.group(2).strip()

    m = _CLIENT_CODE_ONLY_RE.match(folder_name)
    if m:
        return m.group(1), ""

    return "", folder_name


def parse_case_folder(folder_name: str) -> tuple[str, str, str, str]:
    """
    Extract (case_no, case_name, tm_no, class_code) from a case folder name.

    Strategy
    --------
    1. First token matching CASE_NO_RE → case_no
    2. All non-special tokens between case_no and the TM number → case_name
    3. First 6-digit token after case_no → tm_no
    4. Token matching C\\d+ (or "Class <n>") → class_code

    Never raises; missing fields return "".
    """
    folder_name = folder_name.strip()
    parts = folder_name.split()

    case_no = ""
    tm_no = ""
    class_code = ""
    case_name_parts: list[str] = []

    found_case_no = False
    found_tm_no = False

    i = 0
    while i < len(parts):
        part = parts[i]

        if not found_case_no and _CASE_NO_RE.match(part):
            case_no = part
            found_case_no = True

        elif found_case_no and not found_tm_no and _TM_NO_RE.match(part):
            tm_no = part
            found_tm_no = True

        elif found_case_no and not found_tm_no:
            # Could be class token appearing before TM number (or without one)
            if _CLASS_CODE_RE.match(part):
                class_code = part.upper()
            elif part.lower() == "class" and i + 1 < len(parts) and parts[i + 1].isdigit():
                class_code = f"C{parts[i + 1]}"
                i += 1  # consume the digit token
            else:
                # Tokens between case_no and TM number → brand/case name
                case_name_parts.append(part)

        elif found_tm_no:
            # After TM number: look for class code
            if _CLASS_CODE_RE.match(part):
                class_code = part.upper()
            elif part.lower() == "class" and i + 1 < len(parts) and parts[i + 1].isdigit():
                class_code = f"C{parts[i + 1]}"
                i += 1  # consume the digit token

        i += 1

    case_name = " ".join(case_name_parts)
    return case_no, case_name, tm_no, class_code


def extract_full_case_name(folder_name: str, tm_no: str) -> str:
    """
    Legacy helper — kept for backward compatibility.

    With the improved parse_case_folder() this is rarely needed, but it is
    preserved so callers that relied on it continue to work correctly.
    """
    if not tm_no:
        return ""

    parts = folder_name.split()
    case_name_parts: list[str] = []
    found_case_no = False

    for part in parts:
        if _CASE_NO_RE.match(part):
            found_case_no = True
            continue
        if part == tm_no:
            break
        if found_case_no and not _CLASS_CODE_RE.match(part):
            case_name_parts.append(part)

    return " ".join(case_name_parts)


# ---------------------------------------------------------------------------
# Client validation helper
# ---------------------------------------------------------------------------

def validate_client_folder(folder_name: str) -> dict:
    """
    Return a dict with parsed fields plus a 'warnings' list.

    Warnings are generated for:
    - Missing client number
    - Missing client name
    """
    client_number, client_name = parse_client_folder(folder_name)
    warnings: list[str] = []

    if not client_number:
        warnings.append(f"Could not extract client code from: '{folder_name}'")
    if not client_name:
        warnings.append(f"Client name is empty for folder: '{folder_name}'")

    return {
        "client_number": client_number,
        "client_name": client_name,
        "warnings": warnings,
    }
