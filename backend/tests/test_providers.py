"""LLM provider catalog and settings API tests."""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ["OPENMINIAGENTS_STUB_RUN"] = "1"
os.environ["OPENMINIAGENTS_DATA_DIR"] = "/tmp/openminiagents-provider-test"

from openminiagents.app import create_app
from openminiagents.llm_providers import build_adk_model, catalog_for_api, get_provider


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def test_catalog_includes_browseros_style_providers():
    ids = {p["id"] for p in catalog_for_api()}
    assert "gemini" in ids
    assert "openai" in ids
    assert "anthropic" in ids
    assert "ollama" in ids
    assert "lmstudio" in ids
    assert "chatgpt_oauth" in ids


def test_build_gemini_native_model():
    resolved = build_adk_model("gemini", "gemini-2.5-flash")
    assert resolved.provider_id == "gemini"
    assert resolved.adk_model == "gemini-2.5-flash"


def test_chatgpt_oauth_needs_connect():
    from openminiagents.chatgpt_oauth import delete_tokens

    delete_tokens()
    with pytest.raises(ValueError, match="not connected"):
        build_adk_model("chatgpt_oauth", "gpt-5.2")


@pytest.mark.anyio
async def test_providers_api(client: AsyncClient) -> None:
    r = await client.get("/api/providers")
    assert r.status_code == 200
    body = r.json()
    assert "providers" in body
    assert "settings" in body


@pytest.mark.anyio
async def test_update_settings(client: AsyncClient) -> None:
    r = await client.put(
        "/api/providers/settings",
        json={"default_provider_id": "gemini", "default_model_id": "gemini-2.5-flash"},
    )
    assert r.status_code == 200
    assert r.json()["settings"]["default_provider_id"] == "gemini"


@pytest.mark.anyio
async def test_ollama_test_endpoint(client: AsyncClient) -> None:
    """May fail if Ollama not running — skip connection errors in CI."""
    r = await client.post(
        "/api/providers/test",
        json={"provider_id": "ollama", "model_id": "llama3.1"},
    )
    if r.status_code == 200:
        assert r.json()["ok"] is True
    else:
        assert r.status_code == 502
