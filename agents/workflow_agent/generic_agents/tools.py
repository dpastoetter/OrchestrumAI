"""Tools used by generic workflow sub-agents."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx
from google.adk.tools.function_tool import FunctionTool

_BACKEND = Path(__file__).resolve().parent.parent.parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from orchestrumai.safe_url import UnsafeUrlError, validate_http_url  # noqa: E402


def fetch_url(url: str) -> dict[str, str]:
    """Fetch a public HTTP(S) URL and return a text excerpt for analysis."""
    url = (url or "").strip()
    try:
        url = validate_http_url(url, allow_private=False)
    except UnsafeUrlError as exc:
        return {"error": str(exc), "content": ""}
    try:
        # Do not follow redirects to avoid hopping into private networks.
        with httpx.Client(timeout=20.0, follow_redirects=False) as client:
            response = client.get(url, headers={"User-Agent": "OrchestrumAI/1.0"})
            if response.is_redirect:
                return {"error": "Redirects are not followed for safety", "content": ""}
            response.raise_for_status()
            text = response.text
    except Exception as exc:
        return {"error": str(exc), "content": ""}
    # Strip excessive length for LLM context
    excerpt = text[:50_000]
    return {"url": url, "content": excerpt, "length": str(len(text))}


fetch_url_tool = FunctionTool(fetch_url)
