"""Grep Doc: keyword search in local uploads."""

from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent

from .doc_tools import grep_doc_tool, read_local_excerpt_tool

_INSTRUCTION = """You search uploaded local documents for keywords.

1. Call grep_doc with the user's search terms (try variants if needed).
2. Summarize matches with line snippets and counts.
3. If no file_path, ask the coordinator to ensure a file was uploaded."""


def build_grep_doc_agent(model: Any) -> LlmAgent:
    return LlmAgent(
        name="grep_doc_agent",
        description="Search for keywords in local uploaded documents.",
        instruction=_INSTRUCTION,
        model=model,
        tools=[grep_doc_tool, read_local_excerpt_tool],
    )
