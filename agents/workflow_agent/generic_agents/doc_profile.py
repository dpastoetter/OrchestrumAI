"""Doc Profile: one-screen file summary."""

from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent

from .doc_tools import doc_profile_tool, ocr_check_tool, peek_table_tool

_INSTRUCTION = """You produce a concise document profile for files in data/uploads.

1. Call doc_profile on the session file.
2. Report: file type, size, OCR/scan risk, table vs text, and a short readiness summary.
3. Note if the user should use table_peek or text_extract next."""


def build_doc_profile_agent(model: Any) -> LlmAgent:
    return LlmAgent(
        name="doc_profile_agent",
        description="Profiles local uploads: type, tables, OCR risk, text sample.",
        instruction=_INSTRUCTION,
        model=model,
        tools=[doc_profile_tool, ocr_check_tool, peek_table_tool],
    )
