"""Automation preferences: inbox watch, webhooks, export paths."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from .config import DATA_DIR, ensure_data_dir

log = logging.getLogger(__name__)

_SETTINGS_PATH = DATA_DIR / "automation_settings.json"


@dataclass
class AutomationSettings:
    inbox_watch_enabled: bool = True
    webhook_url: str = ""
    markdown_export_dir: str = ""
    desktop_notify: bool = False


def _load_raw() -> dict:
    ensure_data_dir()
    if not _SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Could not read automation settings: %s", exc)
        return {}


def _save_raw(data: dict) -> None:
    ensure_data_dir()
    _SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_automation_settings() -> AutomationSettings:
    raw = _load_raw()
    return AutomationSettings(
        inbox_watch_enabled=bool(raw.get("inbox_watch_enabled", True)),
        webhook_url=str(raw.get("webhook_url", "")).strip(),
        markdown_export_dir=str(raw.get("markdown_export_dir", "")).strip(),
        desktop_notify=bool(raw.get("desktop_notify", False)),
    )


def update_automation_settings(
    *,
    inbox_watch_enabled: bool | None = None,
    webhook_url: str | None = None,
    markdown_export_dir: str | None = None,
    desktop_notify: bool | None = None,
) -> AutomationSettings:
    raw = _load_raw()
    if inbox_watch_enabled is not None:
        raw["inbox_watch_enabled"] = inbox_watch_enabled
    if webhook_url is not None:
        raw["webhook_url"] = webhook_url.strip()
    if markdown_export_dir is not None:
        raw["markdown_export_dir"] = markdown_export_dir.strip()
    if desktop_notify is not None:
        raw["desktop_notify"] = desktop_notify
    _save_raw(raw)
    return get_automation_settings()


def settings_for_api() -> dict:
    from .config import DATA_DIR, UPLOADS_DIR

    s = get_automation_settings()
    return {
        "inbox_watch_enabled": s.inbox_watch_enabled,
        "webhook_url": s.webhook_url,
        "markdown_export_dir": s.markdown_export_dir,
        "desktop_notify": s.desktop_notify,
        "inbox_dir": str((DATA_DIR / "inbox").resolve()),
        "uploads_dir": str(UPLOADS_DIR.resolve()),
        "data_dir": str(DATA_DIR.resolve()),
    }
