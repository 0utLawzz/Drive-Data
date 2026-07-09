"""
Token definitions for Parser V2.

A folder name is tokenized into a flat sequence of typed tokens. Every
downstream extraction (client number, case number, TM number, class code,
case name) operates on this token stream instead of re-running ad-hoc regexes
against the raw string. This makes the "confirmed business rules" (see
PROJECT_BIBLE.md) explicit, testable in isolation, and easy to extend without
risking regressions in unrelated fields.
"""

from dataclasses import dataclass
from enum import Enum


class TokenType(str, Enum):
    CLIENT_NO = "CLIENT_NO"   # e.g. A-001
    CASE_NO = "CASE_NO"       # e.g. A001-001 or A52-029 (2- or 3-digit prefix)
    TM_NO = "TM_NO"           # exactly 6 digits, e.g. 123456
    CLASS = "CLASS"           # C + 1-2 digits, e.g. C01, C7
    DATE = "DATE"             # DD-MM-YYYY
    WORD = "WORD"             # alphabetic word, any case — becomes part of case name
    NUM = "NUM"               # any other bare number (not TM_NO shaped)
    OTHER = "OTHER"           # anything that matches none of the above


@dataclass(frozen=True)
class Token:
    type: TokenType
    raw: str          # original text of this token
    position: int      # index within the tokenized sequence

    def __repr__(self) -> str:  # pragma: no cover - debug convenience
        return f"{self.type.value}({self.raw!r})"
