"""
Confirmed business rules applied by Parser V2.

These mirror the "Confirmed Business Rules" table in docs/PROJECT_PROGRESS.md
(BR-1..BR-7). Keeping them named and documented here — rather than inlined in
parser.py — means a future sprint can audit rule coverage at a glance.

BR-1: TM Number is optional in folder names. Not every case has a TM number
      at filing time.
BR-2: Missing TM Number is a WARNING, not a parse failure. The record is
      still generated; the TM No field is left blank.
BR-3: Missing Class code is a WARNING, not a parse failure. Same treatment
      as missing TM No.
BR-4: Duplicate detection should primarily use TM Number as the most stable
      unique identifier. (Applied by callers via the composite key; Parser V2
      does not deduplicate itself — see parser_v2.directory.process_directory.)
BR-5: NTN and similar administrative case types may never have a TM Number.
      Folders like "A51-016 M TAHIR NTN" are valid records, not naming errors.
      (Consequence: parser must never fail a case solely for lacking a TM No.)
BR-6: Empty case folders are still counted as records. Callers must include
      every case folder in output regardless of file contents.
BR-7: DATE ADDED is excluded from comparison keys. (Applies to
      compare_outputs.py, not this parser — noted here for completeness.)

Severity classification (decision 2026-07-09-C2, preserved in V2):
  - is_failure  = missing Case # only (the one field with no legitimate
                  reason to be absent from a well-formed folder name).
  - is_warning  = missing TM No and/or missing Class code, provided the
                  Case # was found (i.e. not already a failure).
  - is_ok       = no missing fields at all.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Severity:
    is_failure: bool
    is_warning: bool
    is_ok: bool
    issues: List[str]
    warnings: List[str]


def classify_case_severity(case_no: str, tm_no: str, class_code: str) -> Severity:
    """Apply BR-2/BR-3/BR-5 severity rules to a parsed case's fields."""
    issues: List[str] = []
    warnings: List[str] = []

    if not case_no:
        issues.append("missing Case # (expected pattern like A001-001 or A52-029)")
    if not tm_no:
        # BR-2 / BR-5: optional field — never a failure on its own.
        warnings.append("missing TM No (expected 6-digit number)")
    if not class_code:
        # BR-3: optional field — never a failure on its own.
        warnings.append("missing Class code (expected C01, C29, etc.)")

    is_failure = not case_no
    is_warning = (not is_failure) and bool(warnings)
    is_ok = not issues and not warnings

    return Severity(
        is_failure=is_failure,
        is_warning=is_warning,
        is_ok=is_ok,
        issues=issues,
        warnings=warnings,
    )
