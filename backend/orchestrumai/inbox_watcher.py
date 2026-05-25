"""Watch data/inbox for new files and create workflow requests."""

from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks

from .automation_settings import get_automation_settings
from .config import DATA_DIR, DEFAULT_USER_ID, UPLOADS_DIR, ensure_data_dir
from .file_storage import ALLOWED_EXTENSIONS
from .request_service import create_request_impl
from .runner_bridge import get_runner_bridge

log = logging.getLogger(__name__)

INBOX_DIR = DATA_DIR / "inbox"
_PROCESSED_DIR = INBOX_DIR / ".processed"
_seen: set[str] = set()


def _ensure_inbox_dirs() -> None:
    ensure_data_dir()
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    _PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


async def scan_inbox(background: BackgroundTasks | None = None) -> int:
    settings = get_automation_settings()
    if not settings.inbox_watch_enabled:
        return 0
    _ensure_inbox_dirs()
    bg = background or BackgroundTasks()
    bridge = get_runner_bridge()
    created = 0

    for path in sorted(INBOX_DIR.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue
        key = f"{path.name}:{path.stat().st_mtime_ns}"
        if key in _seen:
            continue

        stored_name = f"inbox_{path.stem}_{int(datetime.now(timezone.utc).timestamp())}{path.suffix.lower()}"
        dest = UPLOADS_DIR / stored_name
        shutil.copy2(path, dest)
        title = f"Inbox: {path.name}"
        description = (
            f"Process the file uploaded to the inbox folder.\n"
            f"Original path: {path.name}\n"
            f"Use private document specialists as needed."
        )

        try:
            await create_request_impl(
                background=bg,
                bridge=bridge,
                user_id=DEFAULT_USER_ID,
                title=title,
                description=description,
                priority="normal",
                agent_type="workflow",
                file_path=str(dest.resolve()),
                file_name=path.name,
                run_source="inbox",
            )
            shutil.move(str(path), str(_PROCESSED_DIR / path.name))
            _seen.add(key)
            created += 1
            log.info("Inbox watcher created request for %s", path.name)
        except Exception as exc:
            log.exception("Inbox processing failed for %s: %s", path, exc)

    return created


async def inbox_tick() -> None:
    from .scheduler_service import get_scheduler_service

    svc = get_scheduler_service()
    bg = svc._pending_background or BackgroundTasks()
    await scan_inbox(bg)
