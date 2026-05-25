"""Tools used by generic workflow sub-agents."""

from __future__ import annotations

import httpx
from google.adk.tools.function_tool import FunctionTool


def fetch_url(url: str) -> dict[str, str]:
    """Fetch a public HTTP(S) URL and return a text excerpt for analysis."""
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return {"error": "URL must start with http:// or https://", "content": ""}
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            response = client.get(url, headers={"User-Agent": "OrchestrumAI/1.0"})
            response.raise_for_status()
            text = response.text
    except Exception as exc:
        return {"error": str(exc), "content": ""}
    # Strip excessive length for LLM context
    excerpt = text[:50_000]
    return {"url": url, "content": excerpt, "length": str(len(text))}


fetch_url_tool = FunctionTool(fetch_url)
