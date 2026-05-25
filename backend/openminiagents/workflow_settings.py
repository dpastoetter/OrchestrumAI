"""Persisted toggles for General workflow generic sub-agents."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from .config import DATA_DIR, ensure_data_dir

log = logging.getLogger(__name__)

_SETTINGS_PATH = DATA_DIR / "workflow_settings.json"


@dataclass
class WorkflowSettings:
    enabled_generic_agents: list[str]


def _load_raw() -> dict:
    ensure_data_dir()
    if not _SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Could not read workflow settings: %s", exc)
        return {}


def _save_raw(data: dict) -> None:
    ensure_data_dir()
    _SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_workflow_settings() -> WorkflowSettings:
    from workflow_agent.generic_agents.catalog import default_enabled_ids

    raw = _load_raw()
    enabled = raw.get("enabled_generic_agents")
    if not isinstance(enabled, list):
        enabled = default_enabled_ids()
    return WorkflowSettings(enabled_generic_agents=enabled)


def update_workflow_settings(*, enabled_generic_agents: list[str] | None = None) -> WorkflowSettings:
    raw = _load_raw()
    if enabled_generic_agents is not None:
        raw["enabled_generic_agents"] = enabled_generic_agents
    _save_raw(raw)
    return get_workflow_settings()


def resolve_enabled_for_request(request_override: list[str] | None) -> list[str]:
    """Resolve enabled generic agent IDs for a new workflow request."""
    from workflow_agent.generic_agents.catalog import resolve_enabled_ids

    global_settings = get_workflow_settings()
    return resolve_enabled_ids(
        global_settings.enabled_generic_agents,
        request_override,
    )


def settings_for_api() -> dict:
    s = get_workflow_settings()
    return {"enabled_generic_agents": s.enabled_generic_agents}
