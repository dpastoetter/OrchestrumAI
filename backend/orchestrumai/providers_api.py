"""API for LLM provider catalog and settings."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .llm_providers import (
    build_adk_model,
    catalog_for_api,
    get_provider,
    provider_connection_status,
)
from . import chatgpt_oauth
from .provider_settings import get_provider_settings, settings_for_api, update_provider_settings
from .safe_url import UnsafeUrlError, validate_http_url

log = logging.getLogger(__name__)

router = APIRouter(tags=["providers"])


class UpdateSettingsBody(BaseModel):
    default_provider_id: str | None = None
    default_model_id: str | None = None
    api_keys: dict[str, str] = Field(default_factory=dict)
    ollama_host: str | None = None
    lm_studio_base_url: str | None = None


class TestProviderBody(BaseModel):
    provider_id: str
    model_id: str | None = None


class ChatGPTOAuthCallbackBody(BaseModel):
    session_id: str
    callback_url: str


def _validate_local_provider_url(url: str | None, field: str) -> str | None:
    if url is None:
        return None
    cleaned = url.strip()
    if not cleaned:
        return ""
    try:
        # Local LLM hosts are expected on loopback/LAN.
        return validate_http_url(cleaned, allow_private=True)
    except UnsafeUrlError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field}: {exc}") from exc


@router.get("/providers")
async def list_providers() -> dict:
    return {"providers": catalog_for_api(), "settings": settings_for_api()}


@router.put("/providers/settings")
async def put_settings(body: UpdateSettingsBody) -> dict:
    if body.default_provider_id and get_provider(body.default_provider_id) is None:
        raise HTTPException(status_code=400, detail="Unknown provider_id")
    ollama_host = _validate_local_provider_url(body.ollama_host, "ollama_host")
    lm_studio_base_url = _validate_local_provider_url(body.lm_studio_base_url, "lm_studio_base_url")
    update_provider_settings(
        default_provider_id=body.default_provider_id,
        default_model_id=body.default_model_id,
        api_keys=body.api_keys or None,
        ollama_host=ollama_host,
        lm_studio_base_url=lm_studio_base_url,
    )
    from .runner_bridge import get_runner_bridge

    get_runner_bridge().clear_runner_cache()
    return {"settings": settings_for_api(), "providers": catalog_for_api()}


@router.post("/providers/test")
async def test_provider(body: TestProviderBody) -> dict:
    """Quick connectivity check (local ping or minimal completion)."""
    provider = get_provider(body.provider_id)
    if provider is None:
        raise HTTPException(status_code=400, detail="Unknown provider")

    status = provider_connection_status(provider)
    if status == "coming_soon":
        raise HTTPException(
            status_code=501,
            detail=f"{provider.name} OAuth is not implemented yet.",
        )
    if provider.id == "chatgpt_oauth" and status == "needs_config":
        raise HTTPException(
            status_code=400,
            detail="Connect ChatGPT in Settings (OAuth) before testing.",
        )
    if status == "needs_config" and provider.auth_type == "api_key":
        raise HTTPException(
            status_code=400,
            detail=f"Configure environment: {', '.join(provider.env_vars)}",
        )

    if provider.id == "ollama":
        host = get_provider_settings().ollama_host.rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{host}/api/tags")
                r.raise_for_status()
            return {"ok": True, "message": f"Ollama reachable at {host}"}
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    if provider.id == "lmstudio":
        base = get_provider_settings().lm_studio_base_url.rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{base}/models")
                r.raise_for_status()
            return {"ok": True, "message": f"LM Studio reachable at {base}"}
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    try:
        resolved = build_adk_model(body.provider_id, body.model_id)
        return {
            "ok": True,
            "message": f"Model resolved: {resolved.display_name}",
            "provider_id": resolved.provider_id,
            "model_id": resolved.model_id,
        }
    except Exception as exc:
        log.exception("Provider test failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/providers/chatgpt-oauth/status")
async def chatgpt_oauth_status() -> dict:
    return chatgpt_oauth.oauth_status()


@router.post("/providers/chatgpt-oauth/connect")
async def chatgpt_oauth_connect() -> dict:
    """Start OAuth: open authorize_url in a browser; callback server listens on localhost."""
    try:
        result = chatgpt_oauth.start_connect()
        return {
            "session_id": result.session_id,
            "authorize_url": result.authorize_url,
            "redirect_uri": result.redirect_uri,
            "callback_port": result.callback_port,
        }
    except Exception as exc:
        log.exception("ChatGPT OAuth connect failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/providers/chatgpt-oauth/session/{session_id}")
async def chatgpt_oauth_session(session_id: str) -> dict:
    return chatgpt_oauth.get_session_status(session_id)


@router.post("/providers/chatgpt-oauth/callback")
async def chatgpt_oauth_callback(body: ChatGPTOAuthCallbackBody) -> dict:
    """Paste full localhost callback URL if the automatic redirect did not complete."""
    try:
        return chatgpt_oauth.complete_with_callback_url(body.session_id, body.callback_url)
    except Exception as exc:
        log.exception("ChatGPT OAuth callback failed")
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/providers/chatgpt-oauth/disconnect")
async def chatgpt_oauth_disconnect() -> dict:
    chatgpt_oauth.delete_tokens()
    from .runner_bridge import get_runner_bridge

    get_runner_bridge().clear_runner_cache()
    return {"ok": True, "connected": False}
