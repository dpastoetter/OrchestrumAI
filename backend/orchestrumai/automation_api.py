"""Automation settings and inbox scan API."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from .automation_settings import settings_for_api, update_automation_settings
from .inbox_watcher import scan_inbox

router = APIRouter(tags=["automation"])


class UpdateAutomationSettingsBody(BaseModel):
    inbox_watch_enabled: bool | None = None
    webhook_url: str | None = None
    markdown_export_dir: str | None = None
    desktop_notify: bool | None = None


@router.get("/automation/settings")
async def get_settings() -> dict:
    return {"settings": settings_for_api()}


@router.put("/automation/settings")
async def put_settings(body: UpdateAutomationSettingsBody) -> dict:
    update_automation_settings(
        inbox_watch_enabled=body.inbox_watch_enabled,
        webhook_url=body.webhook_url,
        markdown_export_dir=body.markdown_export_dir,
        desktop_notify=body.desktop_notify,
    )
    return {"settings": settings_for_api()}


@router.post("/automation/scan-inbox")
async def trigger_inbox_scan(background: BackgroundTasks) -> dict:
    count = await scan_inbox(background)
    return {"created": count}
