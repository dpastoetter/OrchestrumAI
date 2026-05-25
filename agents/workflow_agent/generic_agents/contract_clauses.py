"""Clause Finder: locate key contract sections in local text."""

from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent

from .doc_tools import read_local_excerpt_tool

_INSTRUCTION = """You find important clauses in contracts and legal documents (local text only).

Call read_local_excerpt for uploaded files. Search for and quote briefly:
- Term / termination / notice period
- Payment / fees
- Liability / indemnity
- Confidentiality
- Governing law / jurisdiction
- SLA or performance (if any)

For each clause found: name, short quote (under 300 chars), and location hint (page/section if visible).
If not found, list as "not found". This is not legal advice."""


def build_contract_clauses_agent(model: Any) -> LlmAgent:
    return LlmAgent(
        name="contract_clauses_agent",
        description="Locates key clauses in local contracts (termination, payment, liability, etc.).",
        instruction=_INSTRUCTION,
        model=model,
        tools=[read_local_excerpt_tool],
    )
