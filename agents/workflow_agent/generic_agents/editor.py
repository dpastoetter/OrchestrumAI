"""Editor sub-agent: reviews drafts and returns feedback."""

from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent

_INSTRUCTION = """You are an editor. Given a request string (usually containing a draft),
return concise structured feedback: strengths, issues, and specific suggested edits.
Do not rewrite the full document unless the brief asks for a revised version."""


def build_editor_agent(model: Any) -> LlmAgent:
    return LlmAgent(
        name="editor_agent",
        description=(
            "Reviews a draft and returns concise feedback and suggested edits. "
            "Use before finalizing important written output."
        ),
        instruction=_INSTRUCTION,
        model=model,
        tools=[],
    )
