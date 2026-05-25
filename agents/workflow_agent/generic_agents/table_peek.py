"""Table Peek: preview CSV/XLSX/PDF tables without Sheets export."""

from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent

from .doc_tools import peek_table_tool

_INSTRUCTION = """You preview tabular data from a local uploaded file (session file_path).

Call peek_table with a short description of what columns matter. Return:
- markdown_preview for the human
- confidence_notes if present
- row_count and column names

Do not write to Google Sheets; preview only."""


def build_table_peek_agent(model: Any) -> LlmAgent:
    return LlmAgent(
        name="table_peek_agent",
        description="Previews spreadsheet or document tables locally (no Sheets write).",
        instruction=_INSTRUCTION,
        model=model,
        tools=[peek_table_tool],
    )
