"""
Parser V2 — token-based folder-name parser for Drive Folders List.

This package is a NEW, additive module. It does not modify `main.py` or any
existing parsing logic (architecture decision: "main.py never modified unless
a confirmed bug is found in an isolated, reviewed change"). Parser V2 is meant
to be adopted deliberately by callers (batch_export.py --engine v2,
validate_parser_v2.py) — the legacy engine remains the default everywhere
until a future sprint promotes V2.

Public API mirrors the legacy functions in `main.py` 1:1 so callers can swap
engines without changing call sites:

    parse_client_folder(folder_name)      -> (client_number, client_name)
    parse_case_folder(folder_name)        -> (case_no, case_name, tm_no, class_code)
    extract_full_case_name(folder_name, tm_no) -> case_name
    process_directory(base_path, prefix_to_remove, max_records=None) -> list[dict]

See PROJECT_BIBLE.md for the full architecture write-up and the confirmed
business rules (BR-1..BR-7) this parser implements.
"""

from .parser import (
    parse_client_folder,
    parse_case_folder,
    extract_full_case_name,
    diagnose_case,
    diagnose_client,
)
from .directory import process_directory

__all__ = [
    "parse_client_folder",
    "parse_case_folder",
    "extract_full_case_name",
    "diagnose_case",
    "diagnose_client",
    "process_directory",
]
