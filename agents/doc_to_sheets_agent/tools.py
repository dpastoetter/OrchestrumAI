"""Tools for document extraction and Google Sheets export."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from google.adk.tools import ToolContext
from google.adk.tools.function_tool import FunctionTool

from workflow_agent.state_schema import WorkflowStep

# Backend helpers on PYTHONPATH when run via uvicorn
_BACKEND = Path(__file__).resolve().parent.parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def _set_step(tool_context: ToolContext, step: str, **extra: str) -> dict[str, str]:
    tool_context.state["current_step"] = step
    for key, value in extra.items():
        tool_context.state[key] = value
    return {"current_step": step, **extra}


def parse_document(tool_context: ToolContext) -> dict[str, object]:
    """Read the uploaded file and extract structured rows into session state."""
    file_path = str(tool_context.state.get("file_path", ""))
    if not file_path:
        return {"error": "No file_path in session state"}

    from openminiagents.config import STUB_RUN
    from openminiagents.document_parser import default_column_mapping, extract_table

    description = str(tool_context.state.get("request_description", ""))
    mime_type = str(tool_context.state.get("file_mime_type", ""))
    provider_id = str(tool_context.state.get("llm_provider_id", "")) or None
    model_id = str(tool_context.state.get("llm_model_id", "")) or None
    table = extract_table(
        file_path,
        mime_type=mime_type,
        description=description,
        stub=STUB_RUN,
        provider_id=provider_id,
        model_id=model_id,
    )
    columns = table["columns"]
    rows = table["rows"]
    mapping = default_column_mapping(columns)

    tool_context.state["preview_rows_json"] = json.dumps(rows)
    tool_context.state["columns_json"] = json.dumps(columns)
    tool_context.state["column_mapping_json"] = json.dumps(mapping)
    tool_context.state["extraction_source"] = str(table.get("source", ""))
    tool_context.state["confidence_notes"] = str(table.get("confidence_notes", ""))
    tool_context.state["current_step"] = WorkflowStep.PLANNING
    tool_context.state["status_message"] = f"Extracted {len(rows)} rows."

    return {
        "row_count": len(rows),
        "columns": columns,
        "source": table.get("source"),
        "confidence_notes": table.get("confidence_notes"),
    }


def propose_sheet_mapping(
    tool_context: ToolContext,
    mapping_notes: str,
) -> dict[str, object]:
    """Confirm column mapping and prepare for human approval."""
    columns_json = str(tool_context.state.get("columns_json", "[]"))
    columns = json.loads(columns_json)
    mapping = {c: c for c in columns}
    tool_context.state["column_mapping_json"] = json.dumps(mapping)
    tool_context.state["mapping_notes"] = mapping_notes
    return {"column_mapping": mapping, "notes": mapping_notes}


def request_human_approval(
    tool_context: ToolContext,
    approval_summary: str,
) -> dict[str, str]:
    """Pause until the user reviews extracted rows in the UI."""
    preview = json.loads(str(tool_context.state.get("preview_rows_json", "[]")))
    row_count = len(preview)
    return _set_step(
        tool_context,
        WorkflowStep.AWAITING_APPROVAL,
        approval_summary=approval_summary,
        proposed_actions=f"Review {row_count} extracted rows, then approve to write to Google Sheets.",
        status_message=f"Waiting for approval ({row_count} rows).",
        latest_output=f"{row_count} rows ready for review.",
    )


def append_rows_to_sheet(tool_context: ToolContext) -> dict[str, object]:
    """Append approved rows to the target Google Sheet."""
    from openminiagents.config import DEFAULT_SPREADSHEET_ID, STUB_RUN
    from openminiagents.sheets_client import append_rows, parse_spreadsheet_id

    rows = json.loads(str(tool_context.state.get("preview_rows_json", "[]")))
    columns = json.loads(str(tool_context.state.get("columns_json", "[]")))
    sheet_target = str(
        tool_context.state.get("target_sheet_id") or DEFAULT_SPREADSHEET_ID or ""
    )

    tool_context.state["current_step"] = WorkflowStep.EXECUTING
    tool_context.state["status_message"] = "Writing rows to Google Sheets…"

    result = append_rows(
        parse_spreadsheet_id(sheet_target),
        rows,
        columns,
        stub=STUB_RUN,
    )
    tool_context.state["sheet_url"] = str(result["sheet_url"])
    tool_context.state["rows_written"] = str(result["rows_written"])
    return result


def complete_request(tool_context: ToolContext, result_summary: str) -> dict[str, str]:
    """Mark the export as successfully completed."""
    sheet_url = str(tool_context.state.get("sheet_url", ""))
    summary = result_summary
    if sheet_url:
        summary = f"{result_summary}\nSheet: {sheet_url}"
    return _set_step(
        tool_context,
        WorkflowStep.COMPLETED,
        result_summary=summary,
        status_message="Rows written to Google Sheets.",
        latest_output=summary,
    )


def fail_request(tool_context: ToolContext, error_message: str) -> dict[str, str]:
    """Mark the workflow as failed."""
    return _set_step(
        tool_context,
        WorkflowStep.FAILED,
        error_message=error_message,
        status_message=f"Failed: {error_message}",
        latest_output=error_message,
    )


parse_document_tool = FunctionTool(parse_document)
propose_sheet_mapping_tool = FunctionTool(propose_sheet_mapping)
request_human_approval_tool = FunctionTool(request_human_approval)
append_rows_to_sheet_tool = FunctionTool(append_rows_to_sheet)
complete_request_tool = FunctionTool(complete_request)
fail_request_tool = FunctionTool(fail_request)

DOC_TO_SHEETS_TOOLS = [
    parse_document_tool,
    propose_sheet_mapping_tool,
    request_human_approval_tool,
    append_rows_to_sheet_tool,
    complete_request_tool,
    fail_request_tool,
]
