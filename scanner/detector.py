"""
scanner/detector.py — Document pattern detection for Data-Shaper V2.

Patterns are loaded dynamically from config/patterns.json.
All regexes are compiled once at module load for performance.
"""

import re
from utils.helpers import load_patterns
from utils.logger import logger

# ---------------------------------------------------------------------------
# Load & compile patterns at import time (compile once, reuse always)
# ---------------------------------------------------------------------------

_RAW_PATTERNS: dict[str, list[str]] = load_patterns()

# Compiled: { category: [compiled_re, …] }
_COMPILED_PATTERNS: dict[str, list[re.Pattern]] = {}

for _category, _pattern_list in _RAW_PATTERNS.items():
    compiled = []
    for _pat in _pattern_list:
        try:
            compiled.append(re.compile(_pat, re.IGNORECASE))
        except re.error as _e:
            logger.warning("Invalid regex in patterns.json [%s]: %r — %s", _category, _pat, _e)
    _COMPILED_PATTERNS[_category] = compiled

# Tick mark used in output cells
TICK = "✓"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_file_patterns(file_names: str) -> dict[str, str]:
    """
    Scan *file_names* (newline-separated) against every loaded pattern category.

    Returns a dict mapping each category to TICK ("✓") or "" (empty string).
    Categories come from config/patterns.json — no hardcoded lists here.
    """
    if not file_names:
        return {cat: "" for cat in _COMPILED_PATTERNS}

    text = file_names.upper()
    results: dict[str, str] = {}

    for category, compiled_list in _COMPILED_PATTERNS.items():
        matched = any(pat.search(text) for pat in compiled_list)
        results[category] = TICK if matched else ""

    return results


def get_categories() -> list[str]:
    """Return the ordered list of document categories from patterns.json."""
    return list(_COMPILED_PATTERNS.keys())
