"""ChatGPT Plus / Pro OAuth (OpenAI Codex subscription flow)."""

from __future__ import annotations

import json
import logging
import secrets
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from .config import DATA_DIR, ensure_data_dir

log = logging.getLogger(__name__)

OAUTH_TOKEN_PATH = DATA_DIR / "chatgpt_oauth.json"
OAUTH_PENDING_PATH = DATA_DIR / "chatgpt_oauth_pending.json"

CALLBACK_PORTS = (1455, 1457)
CALLBACK_PATH = "/auth/callback"

# In-memory pending sessions (also persisted for restart tolerance)
_pending_lock = threading.Lock()
_pending: dict[str, dict[str, Any]] = {}
_servers: dict[str, HTTPServer] = {}


@dataclass
class OAuthConnectResult:
    session_id: str
    authorize_url: str
    redirect_uri: str
    callback_port: int


def _require_oauth_codex() -> None:
    try:
        import oauth_codex  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Install oauth-codex for ChatGPT OAuth: pip install 'openminiagents[llm]'"
        ) from exc


def token_store():
    _require_oauth_codex()
    from oauth_codex.store import FileTokenStore

    ensure_data_dir()
    return FileTokenStore(path=OAUTH_TOKEN_PATH)


def load_tokens():
    return token_store().load()


def save_tokens(tokens) -> None:
    token_store().save(tokens)


def delete_tokens() -> None:
    token_store().delete()
    with _pending_lock:
        _pending.clear()


def is_connected() -> bool:
    tokens = load_tokens()
    return tokens is not None and bool(tokens.access_token)


def account_summary() -> dict[str, Any] | None:
    tokens = load_tokens()
    if not tokens:
        return None
    return {
        "connected": True,
        "account_id": tokens.account_id,
        "expires_at": tokens.expires_at,
        "scope": tokens.scope,
    }


def get_valid_tokens(*, interactive: bool = False):
    _require_oauth_codex()
    from oauth_codex.auth import discover_endpoints, load_oauth_config, refresh_tokens

    tokens = load_tokens()
    if not tokens:
        if interactive:
            raise ValueError("ChatGPT OAuth not connected. Connect in Settings first.")
        return None

    config = load_oauth_config()
    if tokens.is_expired(leeway_seconds=30):
        if not tokens.refresh_token:
            delete_tokens()
            raise ValueError("ChatGPT OAuth session expired. Reconnect in Settings.")
        with httpx.Client(timeout=30.0) as client:
            config = discover_endpoints(client, config)
            tokens = refresh_tokens(client, config, tokens)
        save_tokens(tokens)
    return tokens


def _load_pending_file() -> None:
    if not OAUTH_PENDING_PATH.exists():
        return
    try:
        data = json.loads(OAUTH_PENDING_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            with _pending_lock:
                _pending.update(data)
    except (OSError, ValueError, TypeError):
        log.warning("Could not read pending OAuth sessions")


def _save_pending_file() -> None:
    ensure_data_dir()
    with _pending_lock:
        OAUTH_PENDING_PATH.write_text(
            json.dumps(_pending, indent=2),
            encoding="utf-8",
        )


def _stop_callback_server(session_id: str) -> None:
    server = _servers.pop(session_id, None)
    if server is not None:
        threading.Thread(target=server.shutdown, daemon=True).start()


class _CallbackHandler(BaseHTTPRequestHandler):
    session_id: str = ""

    def log_message(self, format: str, *args: Any) -> None:
        log.debug("oauth callback: " + format, *args)

    def do_GET(self) -> None:
        if not self.path.startswith(CALLBACK_PATH):
            self.send_error(404)
            return
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if "error" in query:
            err = query.get("error", [""])[0]
            desc = query.get("error_description", [""])[0]
            _mark_session_error(self.session_id, f"{err}: {desc}".strip(": "))
            body = _html_page("Sign-in failed", "You can close this tab and return to OpenMiniAgents.")
        else:
            callback_url = f"http://127.0.0.1:{self.server.server_port}{self.path}"
            try:
                _complete_session_with_callback(self.session_id, callback_url)
                body = _html_page(
                    "Connected",
                    "ChatGPT account linked. You can close this tab and return to OpenMiniAgents.",
                )
            except Exception as exc:
                log.exception("OAuth callback failed")
                _mark_session_error(self.session_id, str(exc))
                body = _html_page("Sign-in failed", str(exc))
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))


def _html_page(title: str, message: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title></head>
<body style="font-family:system-ui;margin:2rem;background:#0f172a;color:#e2e8f0">
<h1>{title}</h1><p>{message}</p>
</body></html>"""


def _mark_session_error(session_id: str, error: str) -> None:
    with _pending_lock:
        if session_id in _pending:
            _pending[session_id]["status"] = "error"
            _pending[session_id]["error"] = error
    _save_pending_file()
    _stop_callback_server(session_id)


def _mark_session_connected(session_id: str) -> None:
    with _pending_lock:
        if session_id in _pending:
            _pending[session_id]["status"] = "connected"
    _save_pending_file()
    _stop_callback_server(session_id)


def _complete_session_with_callback(session_id: str, callback_url: str) -> None:
    _require_oauth_codex()
    from oauth_codex.auth import (
        discover_endpoints,
        exchange_code_for_tokens,
        load_oauth_config,
        parse_callback_url,
    )
    from oauth_codex.auth.config import OAuthConfig

    with _pending_lock:
        pending = _pending.get(session_id)
    if not pending:
        raise ValueError("OAuth session expired or unknown. Start connect again.")
    if pending.get("status") == "connected":
        return

    state = pending["state"]
    code_verifier = pending["code_verifier"]
    config = load_oauth_config()
    config = OAuthConfig(
        client_id=config.client_id,
        scope=config.scope,
        audience=config.audience,
        redirect_uri=pending["redirect_uri"],
        discovery_url=config.discovery_url,
        authorization_endpoint=config.authorization_endpoint,
        token_endpoint=config.token_endpoint,
        originator=config.originator,
    )

    code = parse_callback_url(callback_url, state)
    with httpx.Client(timeout=30.0) as client:
        config = discover_endpoints(client, config)
        tokens = exchange_code_for_tokens(client, config, code, code_verifier)
    save_tokens(tokens)
    _mark_session_connected(session_id)


def start_connect() -> OAuthConnectResult:
    _require_oauth_codex()
    from oauth_codex.auth import (
        build_authorize_url,
        discover_endpoints,
        generate_pkce_pair,
        generate_state,
        load_oauth_config,
    )
    from oauth_codex.auth.config import OAuthConfig

    _load_pending_file()
    code_verifier, code_challenge = generate_pkce_pair()
    state = generate_state()
    session_id = secrets.token_urlsafe(16)

    port = _start_callback_server(session_id)
    redirect_uri = f"http://127.0.0.1:{port}{CALLBACK_PATH}"

    with httpx.Client(timeout=30.0) as client:
        config = discover_endpoints(client, load_oauth_config())
    config = OAuthConfig(
        client_id=config.client_id,
        scope=config.scope,
        audience=config.audience,
        redirect_uri=redirect_uri,
        discovery_url=config.discovery_url,
        authorization_endpoint=config.authorization_endpoint,
        token_endpoint=config.token_endpoint,
        originator=config.originator,
    )
    authorize_url = build_authorize_url(config, state, code_challenge)

    with _pending_lock:
        _pending[session_id] = {
            "state": state,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
            "callback_port": port,
            "status": "pending",
            "created_at": time.time(),
            "error": None,
        }
    _save_pending_file()

    return OAuthConnectResult(
        session_id=session_id,
        authorize_url=authorize_url,
        redirect_uri=redirect_uri,
        callback_port=port,
    )


def _start_callback_server(session_id: str) -> int:
    last_error: Exception | None = None
    for port in CALLBACK_PORTS:
        try:
            handler = type(
                "Handler",
                (_CallbackHandler,),
                {"session_id": session_id},
            )
            server = HTTPServer(("127.0.0.1", port), handler)
            thread = threading.Thread(
                target=server.serve_forever,
                name=f"chatgpt-oauth-{port}",
                daemon=True,
            )
            thread.start()
            _servers[session_id] = server
            return port
        except OSError as exc:
            last_error = exc
            continue
    raise RuntimeError(
        f"Could not bind OAuth callback on ports {CALLBACK_PORTS}: {last_error}"
    )


def get_session_status(session_id: str) -> dict[str, Any]:
    _load_pending_file()
    with _pending_lock:
        pending = _pending.get(session_id)
    if not pending:
        if is_connected():
            return {"status": "connected", "account": account_summary()}
        return {"status": "unknown", "error": "Session not found"}

    status = pending.get("status", "pending")
    out: dict[str, Any] = {
        "status": status,
        "redirect_uri": pending.get("redirect_uri"),
        "callback_port": pending.get("callback_port"),
    }
    if status == "error":
        out["error"] = pending.get("error")
    if status == "connected" or is_connected():
        out["account"] = account_summary()
    return out


def complete_with_callback_url(session_id: str, callback_url: str) -> dict[str, Any]:
    """Manual fallback: user pastes the full localhost callback URL."""
    _complete_session_with_callback(session_id, callback_url.strip())
    return get_session_status(session_id)


def oauth_status() -> dict[str, Any]:
    if is_connected():
        return {"connected": True, "account": account_summary()}
    _load_pending_file()
    active = [
        sid
        for sid, p in _pending.items()
        if p.get("status") == "pending" and time.time() - p.get("created_at", 0) < 600
    ]
    return {
        "connected": False,
        "account": None,
        "pending_sessions": active,
    }
