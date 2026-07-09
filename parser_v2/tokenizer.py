"""
Tokenizer for Parser V2.

Splits a raw folder name on whitespace and classifies each part into a
TokenType. Classification order matters — more specific patterns are tried
before more general ones so, e.g., a CASE_NO never gets misclassified as a
bare NUM.

BR/OI reference (see PROJECT_BIBLE.md and docs/PROJECT_PROGRESS.md):
  - OI-1 fix: CASE_NO now accepts a 2- or 3-digit prefix (`[A-Z]\\d{2,3}-\\d{3}`)
    instead of the legacy 3-digit-only regex. Real Brandex folders use both
    (`A001-001` and `A52-029`); the legacy parser silently dropped the latter.
"""

import re
from typing import List

from .tokens import Token, TokenType

_CLIENT_NO_RE = re.compile(r"^[A-Z]-\d+$")
_CASE_NO_RE = re.compile(r"^[A-Z]\d{2,3}-\d{3}$")     # OI-1 fix baked into V2
_TM_NO_RE = re.compile(r"^\d{6}$")
_CLASS_RE = re.compile(r"^[Cc]\d{1,2}$")
_DATE_RE = re.compile(r"^\d{2}-\d{2}-\d{4}$")
_NUM_RE = re.compile(r"^\d+$")
_WORD_RE = re.compile(r"^[A-Za-z][A-Za-z&.'-]*$")


def _classify(part: str) -> TokenType:
    if _CLIENT_NO_RE.match(part):
        return TokenType.CLIENT_NO
    if _CASE_NO_RE.match(part):
        return TokenType.CASE_NO
    if _TM_NO_RE.match(part):
        return TokenType.TM_NO
    if _CLASS_RE.match(part):
        return TokenType.CLASS
    if _DATE_RE.match(part):
        return TokenType.DATE
    if _NUM_RE.match(part):
        return TokenType.NUM
    if _WORD_RE.match(part):
        return TokenType.WORD
    return TokenType.OTHER


def tokenize(text: str) -> List[Token]:
    """Split `text` on whitespace and classify each part.

    Empty/whitespace-only input returns an empty token list.
    """
    if not text:
        return []
    parts = text.split()
    return [Token(type=_classify(p), raw=p, position=i) for i, p in enumerate(parts)]
