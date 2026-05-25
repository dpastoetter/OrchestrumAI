"""Side effects when request status changes (webhook, export, notify)."""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .automation_settings import get_automation_settings
from .request_store import RequestRecord

log = logging.getLogger(__name__)
_seen_awaiting: set[str] = set()


def on_request_status_change(record: RequestRecord) -> None:
    if record.status == "awaiting_approval":
        _notify_desktop(record)
    if record.status in ("done", "failed"):
        _fire_webhook(record)
    if record.status == "done":
        _export_markdown(record)


def _notify_desktop(record: RequestRecord) -> None:
    settings = get_automation_settings()
    if not settings.desktop_notify:
        return
    if record.id in _seen_awaiting:
        return
    _seen_awaiting.add(record.id)
    try:
        subprocess.run(
            [
                "notify-send",
                "OrchestrumAI",
                f"Approval needed: {record.title}",
            ],
            check=False,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        log.debug("notify-send unavailable")


def _fire_webhook(record: RequestRecord) -> None:
    settings = get_automation_settings()
    url = settings.webhook_url
    if not url:
        return
    try:
        import urllib.request

        payload = json.dumps(
            {
                "event": "request_status",
                "request_id": record.id,
                "status": record.status,
                "title": record.title,
                "current_step": record.current_step,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as exc:
        log.warning("Webhook failed for %s: %s", record.id, exc)


def _export_markdown(record: RequestRecord) -> None:
    settings = get_automation_settings()
    export_dir = settings.markdown_export_dir
    if not export_dir:
        return
    out_root = Path(export_dir).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in record.title)[:60]
    fname = f"{record.id[:8]}_{safe or 'request'}.md"
    path = out_root / fname
    body = [
        f"# {record.title}",
        "",
        f"- Status: {record.status}",
        f"- Step: {record.current_step}",
        f"- Created: {record.created_at}",
        "",
        "## Description",
        "",
        record.description,
        "",
        "## Output",
        "",
        record.latest_output or record.status_message,
    ]
    try:
        path.write_text("\n".join(body), encoding="utf-8")
        log.info("Exported markdown to %s", path)
    except OSError as exc:
        log.warning("Markdown export failed: %s", exc)
