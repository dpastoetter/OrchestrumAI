"""Writer sub-agent: drafts prose from a brief."""

from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent

_INSTRUCTION = """You are a writing specialist. Given a request string, produce clear prose:
emails, summaries, markdown documents, or outlines. Match tone and length implied by the brief.
Return only the draft unless asked for meta-commentary."""


def build_writer_agent(model: Any) -> LlmAgent:
    return LlmAgent(
        name="writer_agent",
        description=(
            "Drafts emails, summaries, and markdown from a brief. "
            "Use when the workflow needs polished written output."
        ),
        instruction=_INSTRUCTION,
        model=model,
        tools=[],
    )
