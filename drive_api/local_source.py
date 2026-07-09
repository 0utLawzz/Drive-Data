"""
Local-directory adapter producing the same `DriveFolder`/`DriveFile` shapes
as `drive_api.scanner` (Sprint 4 Part 6: the parser must not care which
source the data came from).

Used for offline smoke-testing `inventory.py` against `sample_drive/`
without needing live Drive credentials — not part of the production
Sprint 4 workflow, which scans the live Drive via `walk_drive_tree`.
"""

import os
from datetime import datetime, timezone
from typing import Iterator, List, Optional, Tuple

from .models import DriveFolder, DriveFile


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def walk_local_tree(base_path: str, *, max_clients: Optional[int] = None) -> Iterator[Tuple[DriveFolder, Optional[DriveFolder], List[DriveFile]]]:
    """Walk `base_path/<client>/<case>/<files>` and yield the same
    `(client_folder, case_folder, files)` tuples as `walk_drive_tree`,
    including `(client_folder, None, [])` for clients with zero case
    folders so they are not silently dropped from the inventory.
    """
    client_names = sorted(
        n for n in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, n))
    )
    if max_clients:
        client_names = client_names[:max_clients]

    for client_name in client_names:
        client_path = os.path.join(base_path, client_name)
        client_folder = DriveFolder(
            id=client_path, name=client_name, parent_id=base_path,
            created_time="", modified_time="", source="local",
        )
        case_names = sorted(
            n for n in os.listdir(client_path) if os.path.isdir(os.path.join(client_path, n))
        )
        if not case_names:
            yield client_folder, None, []
            continue
        for case_name in case_names:
            case_path = os.path.join(client_path, case_name)
            case_folder = DriveFolder(
                id=case_path, name=case_name, parent_id=client_path,
                created_time="", modified_time="", source="local",
            )
            files = []
            for fname in sorted(os.listdir(case_path)):
                fpath = os.path.join(case_path, fname)
                if not os.path.isfile(fpath):
                    continue
                if fname.lower() == "desktop.ini":
                    continue
                stat = os.stat(fpath)
                files.append(DriveFile(
                    id=fpath, name=fname, parent_id=case_path,
                    mime_type="", size=stat.st_size,
                    created_time=_iso(stat.st_ctime),
                    modified_time=_iso(stat.st_mtime),
                    source="local",
                ))
            yield client_folder, case_folder, files
