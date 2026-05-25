"""Shared Codex (ChatGPT subscription) API client helpers."""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

CODEX_EXTRA_HEADERS = {
    "OpenAI-Beta": "responses=experimental",
    "originator": "codex_cli_rs",
}


def _require_async_client():
    try:
        from oauth_codex import AsyncClient
    except ImportError as exc:
        raise ImportError(
            "Install oauth-codex for ChatGPT OAuth: pip install 'orchestrumai[llm]'"
        ) from exc
    return AsyncClient


def get_async_codex_client():
    from .chatgpt_oauth import token_store

    AsyncClient = _require_async_client()
    return AsyncClient(token_store=token_store())


async def codex_completion_text(
    model: str,
    prompt: str,
    *,
    instructions: str | None = None,
    temperature: float | None = 0.1,
) -> str:
    """Single-turn text completion via Codex /responses API."""
    from .chatgpt_oauth import get_valid_tokens

    get_valid_tokens(interactive=True)
    client = get_async_codex_client()
    try:
        await client.auth.aensure_valid(interactive=False)
        response = await client.responses.create(
            model=model,
            input=prompt,
            instructions=instructions,
            temperature=temperature,
            extra_headers=CODEX_EXTRA_HEADERS,
        )
        if response.error:
            raise RuntimeError(str(response.error))
        return response.output_text or ""
    finally:
        await client.close()


async def codex_responses_create(
    model: str,
    *,
    messages: list[dict[str, Any]] | None = None,
    input_text: str | None = None,
    instructions: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    tool_results: list[Any] | None = None,
    temperature: float | None = None,
) -> Any:
    from .chatgpt_oauth import get_valid_tokens

    get_valid_tokens(interactive=True)
    client = get_async_codex_client()
    try:
        await client.auth.aensure_valid(interactive=False)
        kwargs: dict[str, Any] = {
            "model": model,
            "instructions": instructions,
            "temperature": temperature,
            "extra_headers": CODEX_EXTRA_HEADERS,
        }
        if messages:
            kwargs["messages"] = messages
        if input_text is not None:
            kwargs["input"] = input_text
        if tools:
            kwargs["tools"] = tools
        if tool_results:
            kwargs["tool_results"] = tool_results
        return await client.responses.create(**kwargs)
    finally:
        await client.close()
