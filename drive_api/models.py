"""
Shared data objects returned by every scan source (live Drive API or local
directory mirror).

Per Sprint 4 Part 6, `parser_v2` and `inventory.py` must not know or care
whether a `DriveFolder`/`DriveFile` came from the Google Drive API
(`drive_api.scanner`) or a local path (`drive_api.local_source`) — both
sources populate exactly these fields, using `None`/"" for anything a local
filesystem cannot provide (e.g. a stable Drive file ID or a shareable URL).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DriveFolder:
    id: str                    # Drive file ID, or a synthetic local path-based ID
    name: str
    parent_id: Optional[str]
    created_time: str = ""     # ISO-8601, "" if unknown (local source)
    modified_time: str = ""
    source: str = "drive"       # "drive" | "local"


@dataclass
class DriveFile:
    id: str
    name: str
    parent_id: Optional[str]
    mime_type: str = ""
    size: Optional[int] = None
    created_time: str = ""
    modified_time: str = ""
    source: str = "drive"

    @property
    def extension(self) -> str:
        if "." in self.name:
            return self.name.rsplit(".", 1)[-1].lower()
        return ""

    @property
    def url(self) -> str:
        if self.source == "drive" and self.id:
            return f"https://drive.google.com/file/d/{self.id}/view"
        return ""
