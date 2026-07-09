"""
Online Google Drive traversal.

Replaces the "Drive -> Desktop Sync -> Local Path -> Python" dependency with
a direct "Drive API -> Folder ID -> Python" path (Sprint 4 Part 1). No local
mount or Google Drive Desktop client is required — only a Folder ID and a
Service Account key shared onto that folder.

Mirrors the pagination + thread-local-service pattern already proven in
`validate_drive.py` (decision 2026-07-09-C in docs/PROJECT_PROGRESS.md):
googleapiclient HTTP connections are not thread-safe, so each worker thread
gets its own `service` instance.
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterator, List, Optional, Tuple

from googleapiclient.errors import HttpError

from .models import DriveFolder, DriveFile

FOLDER_MIME = "application/vnd.google-apps.folder"

_thread_local = threading.local()


def _service_for_thread(credentials_path: str):
    """Return a Drive service local to the calling thread (see module docstring)."""
    if not hasattr(_thread_local, "service"):
        from .auth import build_drive_service
        _thread_local.service = build_drive_service(credentials_path)
    return _thread_local.service


def list_children(service, parent_id: str, *, page_size: int = 1000) -> List[dict]:
    """Return all non-trashed direct children of `parent_id` (folders + files), paginated fully."""
    fields = "nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime)"
    q = f"'{parent_id}' in parents and trashed = false"
    items: List[dict] = []
    page_token = None
    while True:
        try:
            resp = service.files().list(
                q=q, fields=fields, pageSize=page_size, pageToken=page_token,
                supportsAllDrives=True, includeItemsFromAllDrives=True,
            ).execute()
        except HttpError as exc:
            raise RuntimeError(f"Drive API error listing children of {parent_id}: {exc}") from exc
        items.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return items


def _split(items: List[dict], parent_id: str) -> Tuple[List[DriveFolder], List[DriveFile]]:
    folders, files = [], []
    for item in items:
        if item.get("mimeType") == FOLDER_MIME:
            folders.append(DriveFolder(
                id=item["id"], name=item["name"], parent_id=parent_id,
                created_time=item.get("createdTime", ""),
                modified_time=item.get("modifiedTime", ""),
                source="drive",
            ))
        else:
            size = item.get("size")
            files.append(DriveFile(
                id=item["id"], name=item["name"], parent_id=parent_id,
                mime_type=item.get("mimeType", ""),
                size=int(size) if size is not None else None,
                created_time=item.get("createdTime", ""),
                modified_time=item.get("modifiedTime", ""),
                source="drive",
            ))
    return folders, files


def walk_drive_tree(
    service_or_credentials_path,
    root_id: str,
    *,
    workers: int = 8,
    max_clients: Optional[int] = None,
) -> Iterator[Tuple[DriveFolder, Optional[DriveFolder], List[DriveFile]]]:
    """Walk a two-level client/case hierarchy rooted at `root_id`.

    Yields `(client_folder, case_folder, files)` for every case folder found
    under every client folder — the same shape `inventory.py` needs to build
    client/case/file records, regardless of source (see drive_api/models.py).
    Clients with zero case folders are still yielded once as
    `(client_folder, None, [])` so they are never silently dropped from the
    client inventory/totals.

    `service_or_credentials_path` should be a credentials-path **string** to
    get real parallel scanning (each worker thread builds its own Drive
    service via `_service_for_thread` — googleapiclient HTTP connections are
    not thread-safe, matching `validate_drive.py`'s proven approach). An
    already-built Drive service object is also accepted for convenience/
    testing, but in that case every request — including the worker pool —
    reuses that single service serially, since a shared connection cannot
    safely be handed to multiple threads.
    """
    if isinstance(service_or_credentials_path, str):
        credentials_path = service_or_credentials_path
        top_service = _service_for_thread(credentials_path)
    else:
        credentials_path = None
        top_service = service_or_credentials_path

    client_items = list_children(top_service, root_id)
    client_folders, _ = _split(client_items, root_id)
    if max_clients:
        client_folders = client_folders[:max_clients]

    def _scan_client(client: DriveFolder):
        svc = _service_for_thread(credentials_path) if credentials_path else top_service
        case_items = list_children(svc, client.id)
        case_folders, _stray_files = _split(case_items, client.id)
        if not case_folders:
            return [(client, None, [])]
        results = []
        for case in case_folders:
            file_items = list_children(svc, case.id)
            _stray_subfolders, files = _split(file_items, case.id)
            results.append((client, case, files))
        return results

    if credentials_path and workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_scan_client, c) for c in client_folders]
            for fut in as_completed(futures):
                for row in fut.result():
                    yield row
    else:
        for c in client_folders:
            for row in _scan_client(c):
                yield row
