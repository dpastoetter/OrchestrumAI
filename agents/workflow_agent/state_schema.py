"""Workflow step constants for session state."""

from __future__ import annotations


class WorkflowStep:
    SUBMITTED = "SUBMITTED"
    PLANNING = "PLANNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


TERMINAL_STEPS = frozenset({WorkflowStep.COMPLETED, WorkflowStep.FAILED})
