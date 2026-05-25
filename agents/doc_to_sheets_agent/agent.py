"""ADK agent: upload document → extract rows → approve → Google Sheets."""

from __future__ import annotations

import os
from typing import Any

from google.adk.agents import LlmAgent

from workflow_agent.state_schema import WorkflowStep

from .tools import DOC_TO_SHEETS_TOOLS

_INSTRUCTION = """You extract tabular data from uploaded documents and export to Google Sheets.

Read `current_step` from session state. The file path is in `file_path`.

1. SUBMITTED — Call `parse_document` (no arguments) to extract rows from the uploaded file.
2. PLANNING — Call `propose_sheet_mapping` with brief mapping_notes, then `request_human_approval`
   with a summary of what will be written (row count, columns).
3. AWAITING_APPROVAL — Wait for human approval in the UI. When resumed with approval, call
   `append_rows_to_sheet`, then `complete_request` with the sheet URL and row count.
   If rejected, call `fail_request`.
4. EXECUTING — Should only happen while writing; finish with `complete_request`.
5. COMPLETED / FAILED — Respond briefly.

Never write to Sheets before approval. Never skip parse_document.
"""


def build_agent(model: Any | None = None) -> LlmAgent:
    resolved = model or os.environ.get("ADK_DEFAULT_MODEL", "gemini-2.5-flash")
    return LlmAgent(
        name="doc_to_sheets_agent",
        description="Extracts structured data from documents and appends rows to Google Sheets after approval.",
        instruction=_INSTRUCTION,
        model=resolved,
        tools=DOC_TO_SHEETS_TOOLS,
    )


root_agent = build_agent()

INITIAL_STATE = {
    "current_step": WorkflowStep.SUBMITTED,
    "status_message": "Document uploaded.",
    "preview_rows_json": "[]",
    "columns_json": "[]",
    "column_mapping_json": "{}",
}
