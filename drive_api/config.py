"""
Configuration for the online Drive scanner.

The root folder ID(s) are read from `settings.json` at the project root, not
hardcoded, so the same code works across different Brandex Drive layouts
without editing Python files. `settings.json` is safe to commit (no
secrets) — only `credentials.json` (the Service Account key) is gitignored.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional

SETTINGS_PATH_DEFAULT = "settings.json"

_DEFAULTS = {
    "credentials_path": "credentials.json",
    "clients_folder_id": "",
    "consultants_folder_id": "",
    "workers": 8,
}


@dataclass
class Settings:
    credentials_path: str
    clients_folder_id: str
    consultants_folder_id: str
    workers: int = 8
    raw: dict = field(default_factory=dict)


def load_settings(path: str = SETTINGS_PATH_DEFAULT) -> Settings:
    """Load settings.json, creating a placeholder file on first run.

    Values passed explicitly as CLI args (in inventory.py) always take
    precedence over settings.json; settings.json is the default so the
    scanner can be re-run without repeating --clients-id/--consultants-id
    every time.
    """
    data = dict(_DEFAULTS)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data.update(json.load(f))
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_DEFAULTS, f, indent=2)
        print(f"⚠️  Created placeholder {path} — fill in clients_folder_id / "
              f"consultants_folder_id (or pass --clients-id / --consultants-id).")

    return Settings(
        credentials_path=data.get("credentials_path", _DEFAULTS["credentials_path"]),
        clients_folder_id=data.get("clients_folder_id", ""),
        consultants_folder_id=data.get("consultants_folder_id", ""),
        workers=int(data.get("workers", _DEFAULTS["workers"])),
        raw=data,
    )
