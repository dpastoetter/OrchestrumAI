"""Automation settings and inbox helpers."""

from __future__ import annotations

import os

import pytest

os.environ["ORCHESTRUMAI_DATA_DIR"] = "/tmp/orchestrumai-automation-test"

from orchestrumai.automation_settings import (
    get_automation_settings,
    update_automation_settings,
)


def test_automation_settings_roundtrip():
    update_automation_settings(
        inbox_watch_enabled=False,
        webhook_url="http://127.0.0.1:9999/hook",
        markdown_export_dir="/tmp/oma-export",
        desktop_notify=True,
    )
    s = get_automation_settings()
    assert s.inbox_watch_enabled is False
    assert s.webhook_url == "http://127.0.0.1:9999/hook"
    assert s.markdown_export_dir == "/tmp/oma-export"
    assert s.desktop_notify is True
