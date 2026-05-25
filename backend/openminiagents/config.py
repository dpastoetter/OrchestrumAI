"""Application configuration."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AGENTS_DIR = PROJECT_ROOT / "agents"
DATA_DIR = Path(os.environ.get("OPENMINIAGENTS_DATA_DIR", PROJECT_ROOT / "data"))
SESSION_DB_PATH = DATA_DIR / "sessions.db"
REQUESTS_DB_PATH = DATA_DIR / "requests.db"

DEFAULT_AGENT_TYPE = "workflow"
DEFAULT_USER_ID = os.environ.get("OPENMINIAGENTS_DEFAULT_USER_ID", "local-user")

UPLOADS_DIR = DATA_DIR / "uploads"
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
DEFAULT_SPREADSHEET_ID = os.environ.get("DEFAULT_SPREADSHEET_ID", "")
SHEETS_WRITE_ENABLED = os.environ.get("SHEETS_WRITE_ENABLED", "1").lower() not in (
    "0",
    "false",
    "no",
)

HOST = os.environ.get("OPENMINIAGENTS_HOST", "127.0.0.1")
PORT = int(os.environ.get("OPENMINIAGENTS_PORT", "8000"))

STUB_RUN = os.environ.get("OPENMINIAGENTS_STUB_RUN", "").lower() in ("1", "true", "yes")


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def session_service_uri() -> str:
    ensure_data_dir()
    return f"sqlite+aiosqlite:///{SESSION_DB_PATH.resolve()}"
