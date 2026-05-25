"""Persisted default LLM provider selection (API keys optional, prefer .env)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .config import DATA_DIR, ensure_data_dir
from .llm_providers import get_provider

log = logging.getLogger(__name__)

_SETTINGS_PATH = DATA_DIR / "llm_settings.json"


@dataclass
class ProviderSettings:
    default_provider_id: str = "gemini"
    default_model_id: str = "gemini-2.5-flash"
    # Optional overrides (single-user local); env vars take precedence when set
    api_keys: dict[str, str] = field(default_factory=dict)
    ollama_host: str = "http://127.0.0.1:11434"
    lm_studio_base_url: str = "http://127.0.0.1:1234/v1"


def _load_raw() -> dict:
    ensure_data_dir()
    if not _SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Could not read LLM settings: %s", exc)
        return {}


def _save_raw(data: dict) -> None:
    ensure_data_dir()
    _SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_provider_settings() -> ProviderSettings:
    raw = _load_raw()
    provider = get_provider(raw.get("default_provider_id", "gemini"))
    default_model = raw.get("default_model_id", "gemini-2.5-flash")
    if provider and not any(m.id == default_model for m in provider.models):
        default_model = provider.models[0].id
    return ProviderSettings(
        default_provider_id=raw.get("default_provider_id", "gemini"),
        default_model_id=default_model,
        api_keys=raw.get("api_keys", {}),
        ollama_host=raw.get("ollama_host", "http://127.0.0.1:11434"),
        lm_studio_base_url=raw.get("lm_studio_base_url", "http://127.0.0.1:1234/v1"),
    )


def update_provider_settings(
    *,
    default_provider_id: str | None = None,
    default_model_id: str | None = None,
    api_keys: dict[str, str] | None = None,
    ollama_host: str | None = None,
    lm_studio_base_url: str | None = None,
) -> ProviderSettings:
    import os

    raw = _load_raw()
    if default_provider_id is not None:
        raw["default_provider_id"] = default_provider_id
    if default_model_id is not None:
        raw["default_model_id"] = default_model_id
    if api_keys is not None:
        existing = raw.get("api_keys", {})
        existing.update({k: v for k, v in api_keys.items() if v})
        raw["api_keys"] = existing
        for env_name, value in existing.items():
            if value:
                os.environ[env_name] = value
    if ollama_host is not None:
        raw["ollama_host"] = ollama_host
        os.environ["OLLAMA_HOST"] = ollama_host
    if lm_studio_base_url is not None:
        raw["lm_studio_base_url"] = lm_studio_base_url
        os.environ["LM_STUDIO_BASE_URL"] = lm_studio_base_url
    _save_raw(raw)
    return get_provider_settings()


def settings_for_api() -> dict:
    s = get_provider_settings()
    return {
        "default_provider_id": s.default_provider_id,
        "default_model_id": s.default_model_id,
        "ollama_host": s.ollama_host,
        "lm_studio_base_url": s.lm_studio_base_url,
        "api_keys_configured": {
            k: bool(v) for k, v in s.api_keys.items()
        },
    }
