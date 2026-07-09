"""
Token-based field extraction for Parser V2.

Each function here has the same name and return shape as its legacy
counterpart in `main.py`, so callers can swap the import and nothing else
changes. Internally, extraction now runs on the tokenized folder name
(see tokenizer.py) rather than re-scanning the raw string with positional
regexes.
"""

from typing import Tuple

from .tokenizer import tokenize
from .tokens import TokenType
from .rules import classify_case_severity


def parse_client_folder(folder_name: str) -> Tuple[str, str]:
    """Extract (client_number, client_name) from a client folder name.

    A client folder is expected to start with a CLIENT_NO token
    (e.g. "A-001") followed by the client's name. If no CLIENT_NO token is
    found, the whole name is treated as the client name (matches legacy
    `main.py` fallback behaviour).
    """
    tokens = tokenize(folder_name)
    if tokens and tokens[0].type is TokenType.CLIENT_NO:
        client_number = tokens[0].raw
        client_name = " ".join(t.raw for t in tokens[1:])
        return client_number, client_name
    return "", folder_name


def parse_case_folder(folder_name: str) -> Tuple[str, str, str, str]:
    """Extract (case_no, case_name, tm_no, class_code) from a case folder name.

    Rules (token-order independent, unlike the legacy single-pass regex):
      - First CASE_NO token found -> case_no.
      - First TM_NO token found -> tm_no.
      - First CLASS token found -> class_code.
      - case_name is derived by extract_full_case_name() below, which knows
        how to bound the name using whichever anchor tokens are present.
    """
    tokens = tokenize(folder_name)

    case_no = ""
    tm_no = ""
    class_code = ""

    for tok in tokens:
        if tok.type is TokenType.CASE_NO and not case_no:
            case_no = tok.raw
        elif tok.type is TokenType.TM_NO and not tm_no:
            tm_no = tok.raw
        elif tok.type is TokenType.CLASS and not class_code:
            class_code = tok.raw

    case_name = extract_full_case_name(folder_name, tm_no)
    if not case_name:
        # Fall back to legacy-style single-word capture: first WORD token
        # immediately after the case number, if any.
        case_name = _fallback_case_name(tokens, case_no)

    return case_no, case_name, tm_no, class_code


def _fallback_case_name(tokens, case_no: str) -> str:
    if not case_no:
        return ""
    seen_case_no = False
    for tok in tokens:
        if tok.type is TokenType.CASE_NO:
            seen_case_no = True
            continue
        if seen_case_no and tok.type is TokenType.WORD:
            return tok.raw
    return ""


def extract_full_case_name(folder_name: str, tm_no: str) -> str:
    """Extract the case name as all WORD/OTHER-but-name-like tokens that sit
    between the case number and the TM number (or, if there is no TM number,
    everything after the case number that isn't a CLASS token).

    This is the token-based equivalent of the legacy string-splitting
    approach in `main.py::extract_full_case_name`, generalised so it no
    longer depends on the TM number always being the delimiter.
    """
    tokens = tokenize(folder_name)
    if not tokens:
        return ""

    name_parts = []
    seen_case_no = False
    for tok in tokens:
        if tok.type is TokenType.CASE_NO:
            seen_case_no = True
            continue
        if not seen_case_no:
            continue
        if tok.type is TokenType.TM_NO:
            break
        if tok.type is TokenType.CLASS:
            continue
        # WORD, NUM (short/free-standing numbers embedded in a name), and
        # OTHER tokens are treated as part of the case name — mirrors legacy
        # behaviour where anything that isn't a recognised code became name text.
        name_parts.append(tok.raw)

    return " ".join(name_parts)


def diagnose_client(folder_name: str) -> dict:
    """Return parse result + issues for a client folder (validator helper)."""
    client_number, client_name = parse_client_folder(folder_name)
    tokens = tokenize(folder_name)
    recognized = bool(tokens) and tokens[0].type is TokenType.CLIENT_NO
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
    """Return full parse result + per-field issues for a case folder.

    Severity classification follows BR-2/BR-3/BR-5 via
    parser_v2.rules.classify_case_severity (decision 2026-07-09-C2):
      - is_failure = missing Case # only.
      - is_warning = missing TM No and/or Class code (Case # present).
      - is_ok      = nothing missing.
    """
    case_no, case_name, tm_no, class_code = parse_case_folder(folder_name)
    severity = classify_case_severity(case_no, tm_no, class_code)

    return {
        "folder_name": folder_name,
        "case_no": case_no,
        "case_name": case_name,
        "tm_no": tm_no,
        "class_code": class_code,
        "issues": severity.issues,
        "warnings": severity.warnings,
        "is_failure": severity.is_failure,
        "is_warning": severity.is_warning,
        "is_ok": severity.is_ok,
    }
