"""Research sub-agent: fetch and summarize web content."""

from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent

from .tools import fetch_url_tool

_INSTRUCTION = """You are a research specialist. Given a request string, gather facts from URLs
(using fetch_url when links are present) or analyze pasted content. Return a concise factual
summary with bullet points. Do not invent sources; say when data is unavailable."""


def build_research_agent(model: Any) -> LlmAgent:
    return LlmAgent(
        name="research_agent",
        description=(
            "Fetches and summarizes information from URLs or long pasted text. "
            "Use for fact-finding during workflow execution."
        ),
        instruction=_INSTRUCTION,
        model=model,
        tools=[fetch_url_tool],
    )
