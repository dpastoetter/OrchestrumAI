"""ChatGPT Pro OAuth flow tests."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

os.environ["ORCHESTRUMAI_STUB_RUN"] = "1"
os.environ["ORCHESTRUMAI_DATA_DIR"] = "/tmp/orchestrumai-chatgpt-oauth-test"

from orchestrumai.app import create_app
from orchestrumai.chatgpt_oauth import delete_tokens, is_connected, start_connect
from orchestrumai.llm_providers import build_adk_model, provider_connection_status, get_provider


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_oauth_tokens():
    delete_tokens()
    yield
    delete_tokens()


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def test_chatgpt_oauth_needs_config_when_disconnected():
    provider = get_provider("chatgpt_oauth")
    assert provider is not None
    assert provider_connection_status(provider) == "needs_config"


def test_build_chatgpt_oauth_raises_when_not_connected():
    with pytest.raises(ValueError, match="not connected"):
        build_adk_model("chatgpt_oauth", "gpt-5.2")


@patch("orchestrumai.chatgpt_oauth._start_callback_server", return_value=1455)
@patch("oauth_codex.auth.discover_endpoints")
@patch("oauth_codex.auth.build_authorize_url", return_value="https://auth.example/authorize")
@patch("oauth_codex.auth.generate_pkce_pair", return_value=("verifier", "challenge"))
@patch("oauth_codex.auth.generate_state", return_value="state123")
@patch("oauth_codex.auth.load_oauth_config")
def test_start_connect_returns_authorize_url(
    mock_config,
    _state,
    _pkce,
    mock_build_url,
    mock_discover,
    _port,
):
    from oauth_codex.auth.config import OAuthConfig

    cfg = OAuthConfig()
    mock_config.return_value = cfg
    mock_discover.return_value = cfg

    result = start_connect()
    assert result.authorize_url == "https://auth.example/authorize"
    assert result.callback_port == 1455
    assert result.session_id


@pytest.mark.anyio
async def test_oauth_status_endpoint(client: AsyncClient) -> None:
    r = await client.get("/api/providers/chatgpt-oauth/status")
    assert r.status_code == 200
    assert r.json()["connected"] is False


@pytest.mark.anyio
@patch("orchestrumai.chatgpt_oauth._start_callback_server", return_value=1455)
@patch("oauth_codex.auth.discover_endpoints")
@patch("oauth_codex.auth.build_authorize_url", return_value="https://auth.example/authorize")
@patch("oauth_codex.auth.generate_pkce_pair", return_value=("verifier", "challenge"))
@patch("oauth_codex.auth.generate_state", return_value="state123")
@patch("oauth_codex.auth.load_oauth_config")
async def test_connect_api(
    mock_config,
    _state,
    _pkce,
    _url,
    mock_discover,
    _port,
    client: AsyncClient,
):
    from oauth_codex.auth.config import OAuthConfig

    cfg = OAuthConfig()
    mock_config.return_value = cfg
    mock_discover.return_value = cfg

    r = await client.post("/api/providers/chatgpt-oauth/connect")
    assert r.status_code == 200
    body = r.json()
    assert "authorize_url" in body
    assert "session_id" in body


@patch("oauth_codex.auth.exchange_code_for_tokens")
@patch("oauth_codex.auth.parse_callback_url", return_value="authcode")
@patch("oauth_codex.auth.discover_endpoints")
@patch("oauth_codex.auth.load_oauth_config")
def test_complete_callback_saves_tokens(
    mock_config,
    mock_discover,
    _parse,
    mock_exchange,
):
    from oauth_codex.auth.config import OAuthConfig
    from oauth_codex.core_types import OAuthTokens

    cfg = OAuthConfig()
    mock_config.return_value = cfg
    mock_discover.return_value = cfg
    mock_exchange.return_value = OAuthTokens(access_token="tok", refresh_token="ref")

    with patch("orchestrumai.chatgpt_oauth._start_callback_server", return_value=1455):
        with patch("oauth_codex.auth.generate_state", return_value="state123"):
            with patch("oauth_codex.auth.generate_pkce_pair", return_value=("v", "c")):
                with patch("oauth_codex.auth.build_authorize_url", return_value="https://x"):
                    result = start_connect()

    from orchestrumai.chatgpt_oauth import complete_with_callback_url

    complete_with_callback_url(
        result.session_id,
        "http://127.0.0.1:1455/auth/callback?code=x&state=state123",
    )
    assert is_connected()


@pytest.mark.anyio
async def test_build_with_saved_tokens(client: AsyncClient) -> None:
    from oauth_codex.core_types import OAuthTokens
    from orchestrumai.chatgpt_oauth import save_tokens

    save_tokens(
        OAuthTokens(
            access_token="test-access",
            refresh_token="test-refresh",
            account_id="acct-test",
        )
    )
    resolved = build_adk_model("chatgpt_oauth", "gpt-5.2")
    from orchestrumai.codex_adk_llm import CodexAdkLlm

    assert isinstance(resolved.adk_model, CodexAdkLlm)
    assert resolved.model_id == "gpt-5.2"
