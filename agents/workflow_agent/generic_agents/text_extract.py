"""Text Extractor: local PDF/text excerpt."""

from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent

from .doc_tools import ocr_check_tool, read_local_excerpt_tool

_INSTRUCTION = """You are a local document text extractor. The user's file is on disk at session
file_path (never fetch URLs).

1. Call read_local_excerpt to pull text (use page_start/page_end for long PDFs).
2. Optionally call ocr_check on PDFs; warn if likely_scanned is true.
3. Return the excerpt plus a one-line summary of what the document contains.

If the tool reports no file_path, ask the coordinator to ensure a file was uploaded or
that text was pasted into the request description."""


def build_text_extract_agent(model: Any) -> LlmAgent:
    return LlmAgent(
        name="text_extract_agent",
        description="Reads text from uploaded local PDF/txt/md files (private, no web).",
        instruction=_INSTRUCTION,
        model=model,
        tools=[read_local_excerpt_tool, ocr_check_tool],
    )
