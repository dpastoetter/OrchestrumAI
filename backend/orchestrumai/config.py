"""Application configuration."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AGENTS_DIR = PROJECT_ROOT / "agents"


def _env(name: str, *, legacy: str | None = None, default: str = "") -> str:
    """Read env var, with optional legacy name from the pre-rename project."""
    value = os.environ.get(name)
    if value:
        return value
    if legacy:
        legacy_value = os.environ.get(legacy)
        if legacy_value:
            return legacy_value
    return default


DATA_DIR = Path(_env("ORCHESTRUMAI_DATA_DIR", legacy="OPENMINIAGENTS_DATA_DIR") or PROJECT_ROOT / "data")
SESSION_DB_PATH = DATA_DIR / "sessions.db"
REQUESTS_DB_PATH = DATA_DIR / "requests.db"

DEFAULT_AGENT_TYPE = "workflow"
DEFAULT_USER_ID = _env("ORCHESTRUMAI_DEFAULT_USER_ID", legacy="OPENMINIAGENTS_DEFAULT_USER_ID", default="local-user")

UPLOADS_DIR = DATA_DIR / "uploads"
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
DEFAULT_SPREADSHEET_ID = os.environ.get("DEFAULT_SPREADSHEET_ID", "")
SHEETS_WRITE_ENABLED = os.environ.get("SHEETS_WRITE_ENABLED", "1").lower() not in (
    "0",
    "false",
    "no",
)

HOST = _env("ORCHESTRUMAI_HOST", legacy="OPENMINIAGENTS_HOST", default="127.0.0.1")
PORT = int(_env("ORCHESTRUMAI_PORT", legacy="OPENMINIAGENTS_PORT", default="8000"))

STUB_RUN = _env("ORCHESTRUMAI_STUB_RUN", legacy="OPENMINIAGENTS_STUB_RUN").lower() in ("1", "true", "yes")


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def session_service_uri() -> str:
    ensure_data_dir()
    return f"sqlite+aiosqlite:///{SESSION_DB_PATH.resolve()}"
