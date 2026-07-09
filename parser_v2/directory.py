"""
Directory-walking layer for Parser V2.

Deliberately mirrors `main.py::process_directory` structurally (same output
columns, same grouping-by-composite-key behaviour, same file/extension
handling) so it is a drop-in replacement for callers that want to try the V2
parsing engine. Only the client/case field-extraction calls are swapped for
the token-based versions in `parser_v2.parser`.

File-pattern tick-mark detection (`check_file_patterns`) is imported directly
from `main.py` — it is unrelated to the folder-name parsing rules this sprint
targets, so it is reused rather than duplicated (keeps a single source of
truth, per the existing "no logic duplication" convention documented in
docs/PROJECT_PROGRESS.md, decision 2026-07-09-A).
"""

import os
from datetime import datetime
from typing import List, Optional

from main import check_file_patterns

from .parser import parse_client_folder, parse_case_folder, extract_full_case_name


def process_directory(base_path: str, prefix_to_remove: str, max_records: Optional[int] = None) -> List[dict]:
    """Process directory and return list of records (Parser V2 engine).

    BR-6: every case folder becomes a record regardless of file contents
    (empty case folders are still counted) — enforced by grouping on
    `case_groups` exactly as the legacy implementation does.
    """
    records = []
    case_groups = {}
    processed_count = 0

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

            full_case_name = extract_full_case_name(case_folder, tm_no)
            if full_case_name:
                case_name = full_case_name

            case_key = (client_number, client_name, case_no, case_name, tm_no, class_code)

            files = []
            for file in os.listdir(case_path):
                file_path = os.path.join(case_path, file)
                if os.path.isfile(file_path):
                    if file.lower() == "desktop.ini":
                        continue

                    file_name, file_ext = os.path.splitext(file)
                    if file_ext.lower() == ".ini":
                        file_ext = ""
                    files.append(f"{file_name}|{file_ext.lstrip('.')}")

            if case_key not in case_groups:
                case_groups[case_key] = []
            case_groups[case_key].extend(files)
            processed_count += 1

    for (client_number, client_name, case_no, case_name, tm_no, class_code), files in case_groups.items():
        file_names = "\n".join([f.split("|")[0] for f in files if f.split("|")[0]])
        file_exts = "\n".join([f.split("|")[1] for f in files if f.split("|")[1]])

        pattern_results = check_file_patterns(file_names)

        record = {
            "CLIENT NUMBER": client_number,
            "CLIENT NAME": client_name,
            "CASE #": case_no,
            "CASE NAME": case_name,
            "TM NO": tm_no,
            "CLASS": class_code,
            "FILES": file_names,
            "EXT": file_exts,
            "DATE ADDED": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        record.update(pattern_results)
        records.append(record)

    return records
