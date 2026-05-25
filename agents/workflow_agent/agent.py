"""Root ADK agent for user-submitted workflow requests."""

from __future__ import annotations

import os
from typing import Any

from google.adk.agents import LlmAgent

from .state_schema import WorkflowStep
from .tools import WORKFLOW_TOOLS

_INSTRUCTION = """You coordinate long-running user requests using an explicit workflow state machine.

Always read `current_step` from session state (not from chat history). Follow this sequence:

1. SUBMITTED — Call `advance_to_planning` with a concise plan_summary derived from the user's goal.
2. PLANNING — Call `request_human_approval` with approval_summary and proposed_actions before doing real work.
3. AWAITING_APPROVAL — Do not advance until the user approves via the UI. When you receive a resume message
   that approval was granted, call `begin_execution`. If rejected, call `fail_request`.
4. EXECUTING — Perform the work (summarize, outline steps, or answer the goal) then call `complete_request`.
5. COMPLETED or FAILED — Respond briefly; do not call more workflow tools.

Keep responses concise. Use tools to update state; never invent step transitions without tools.
"""


def build_agent(model: Any | None = None) -> LlmAgent:
    resolved = model or os.environ.get("ADK_DEFAULT_MODEL", "gemini-2.5-flash")
    return LlmAgent(
        name="workflow_agent",
        description="Processes submitted requests through plan, approval, execution, and completion.",
        instruction=_INSTRUCTION,
        model=resolved,
        tools=WORKFLOW_TOOLS,
    )


# Default export for ADK agent loader
root_agent = build_agent()

INITIAL_STATE = {
    "current_step": WorkflowStep.SUBMITTED,
    "status_message": "Request submitted.",
}
