"""Import bundled personal workflow templates on first run."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .config import DATA_DIR, DEFAULT_USER_ID, PROJECT_ROOT, ensure_data_dir
from .template_store import TemplateStore

log = logging.getLogger(__name__)

_BUNDLED_DIR = PROJECT_ROOT / "data" / "bundled_templates"
_MARKER = DATA_DIR / ".bundled_templates_imported"


def bundled_template_files() -> list[Path]:
    if not _BUNDLED_DIR.is_dir():
        return []
    return sorted(_BUNDLED_DIR.glob("*.json"))


def ensure_bundled_templates_imported(user_id: str | None = None) -> int:
    """Import JSON templates once per data directory. Returns count imported."""
    ensure_data_dir()
    uid = user_id or DEFAULT_USER_ID
    store = TemplateStore()
    imported = 0

    for path in bundled_template_files():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("Skip bundled template %s: %s", path.name, exc)
            continue
        name = str(payload.get("name", "")).strip()
        if not name:
            continue
        if store.find_bundled_by_name(uid, name):
            continue
        topo = payload.get("agent_topology")
        store.create_template(
            user_id=uid,
            name=name,
            description_template=str(payload.get("description_template", "")),
            agent_type=str(payload.get("agent_type", "workflow")),
            agent_topology=json.dumps(topo) if topo else "",
            default_priority=str(payload.get("default_priority", "normal")),
            provider_id=str(payload.get("provider_id", "")),
            model_id=str(payload.get("model_id", "")),
            require_plan_approval=bool(payload.get("require_plan_approval", True)),
            icon=str(payload.get("icon", "")),
            category=str(payload.get("category", "general")),
            bundled=True,
        )
        imported += 1
        log.info("Imported bundled workflow template: %s", name)

    if imported or bundled_template_files():
        _MARKER.write_text(uid, encoding="utf-8")
    return imported
