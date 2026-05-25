"""Workflow tools that advance explicit session state."""

from __future__ import annotations

from google.adk.tools import ToolContext
from google.adk.tools.function_tool import FunctionTool

from .state_schema import WorkflowStep


def _set_step(tool_context: ToolContext, step: str, **extra: str) -> dict[str, str]:
    tool_context.state["current_step"] = step
    for key, value in extra.items():
        tool_context.state[key] = value
    return {"current_step": step, **extra}


def advance_to_planning(
    tool_context: ToolContext,
    plan_summary: str,
) -> dict[str, str]:
    """Move from SUBMITTED to PLANNING and record a short plan summary."""
    return _set_step(
        tool_context,
        WorkflowStep.PLANNING,
        plan_summary=plan_summary,
        status_message="Planning the request.",
    )


def request_human_approval(
    tool_context: ToolContext,
    approval_summary: str,
    proposed_actions: str,
) -> dict[str, str]:
    """Pause the workflow until a human approves or rejects in the UI."""
    return _set_step(
        tool_context,
        WorkflowStep.AWAITING_APPROVAL,
        approval_summary=approval_summary,
        proposed_actions=proposed_actions,
        status_message="Waiting for human approval.",
    )


def begin_execution(
    tool_context: ToolContext,
    execution_notes: str,
) -> dict[str, str]:
    """Start executing the approved plan."""
    return _set_step(
        tool_context,
        WorkflowStep.EXECUTING,
        execution_notes=execution_notes,
        status_message="Executing the approved plan.",
    )


def complete_request(
    tool_context: ToolContext,
    result_summary: str,
) -> dict[str, str]:
    """Mark the workflow as successfully completed."""
    return _set_step(
        tool_context,
        WorkflowStep.COMPLETED,
        result_summary=result_summary,
        status_message="Request completed.",
    )


def fail_request(
    tool_context: ToolContext,
    error_message: str,
) -> dict[str, str]:
    """Mark the workflow as failed."""
    return _set_step(
        tool_context,
        WorkflowStep.FAILED,
        error_message=error_message,
        status_message=f"Failed: {error_message}",
    )


advance_to_planning_tool = FunctionTool(advance_to_planning)
request_human_approval_tool = FunctionTool(request_human_approval)
begin_execution_tool = FunctionTool(begin_execution)
complete_request_tool = FunctionTool(complete_request)
fail_request_tool = FunctionTool(fail_request)

WORKFLOW_TOOLS = [
    advance_to_planning_tool,
    request_human_approval_tool,
    begin_execution_tool,
    complete_request_tool,
    fail_request_tool,
]
