"""
drive_api — Google Drive API access layer (Sprint 4).

All Google Drive API code lives here. Nothing outside this package should
import `googleapiclient` or `google.oauth2` directly — callers (inventory.py,
parser_v2, future modules) work exclusively with the plain data objects in
`drive_api.models` (DriveFolder, DriveFile), so the rest of the codebase never
needs to know whether data came from the live Drive API or a local mirror
(`drive_api.local_source` produces the same shapes for `sample_drive/`).

Public API:
    build_drive_service(credentials_path)      -> googleapiclient Resource
    load_settings(path="settings.json")        -> Settings
    walk_drive_tree(service, root_id, ...)     -> yields (DriveFolder, list[DriveFolder], list[DriveFile])
    walk_local_tree(base_path)                 -> same shape, from a local directory (see local_source.py)
"""

from .auth import build_drive_service
from .config import load_settings, Settings
from .models import DriveFolder, DriveFile
from .scanner import walk_drive_tree, list_children
from .local_source import walk_local_tree

__all__ = [
    "build_drive_service",
    "load_settings",
    "Settings",
    "DriveFolder",
    "DriveFile",
    "walk_drive_tree",
    "list_children",
    "walk_local_tree",
]
