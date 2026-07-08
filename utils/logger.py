"""
Centralised logging for Data-Shaper V2.

Writes:
  logs/scan.log   — INFO and above (every run)
  logs/errors.log — WARNING and above only
Console output uses a simplified format (message only).
"""

import logging
import os
from pathlib import Path

_LOG_DIR = Path(__file__).parent.parent / "logs"


def setup_logger(name: str = "data_shaper") -> logging.Logger:
    """Create (or retrieve) the named logger with file + console handlers."""
    logger = logging.getLogger(name)

    # Guard: don't add handlers more than once (e.g. on module reload)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    os.makedirs(_LOG_DIR, exist_ok=True)

    ts_fmt = "%Y-%m-%d %H:%M:%S"
    file_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", ts_fmt)
    console_fmt = logging.Formatter("%(message)s")

    # scan.log — full run log
    scan_handler = logging.FileHandler(_LOG_DIR / "scan.log", encoding="utf-8")
    scan_handler.setLevel(logging.INFO)
    scan_handler.setFormatter(file_fmt)

    # errors.log — warnings & errors only
    error_handler = logging.FileHandler(_LOG_DIR / "errors.log", encoding="utf-8")
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(file_fmt)

    # Console — INFO messages only (keeps CLI output clean)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_fmt)

    logger.addHandler(scan_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)

    return logger


# Module-level singleton — import this everywhere
logger = setup_logger()
