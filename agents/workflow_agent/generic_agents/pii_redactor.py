"""PII Redactor: mask sensitive fields in local document text."""

from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent

from .doc_tools import read_local_excerpt_tool

_INSTRUCTION = """You redact personally identifiable information from document text.

If the input references a local file, call read_local_excerpt first. Otherwise use the
text provided in your input.

Redact: emails, phone numbers, street addresses, full names when clearly personal,
account/credit card numbers, SSN-style IDs. Replace with tokens like [EMAIL], [PHONE],
[ADDRESS], [NAME], [ACCOUNT].

Return:
1. redacted_text (full text with masks)
2. redaction_manifest (bullet list of what categories were redacted)

Do not invent content. If no PII found, say so and return the original excerpt."""


def build_pii_redactor_agent(model: Any) -> LlmAgent:
    return LlmAgent(
        name="pii_redactor_agent",
        description="Masks PII in local document text before sharing or summarizing.",
        instruction=_INSTRUCTION,
        model=model,
        tools=[read_local_excerpt_tool],
    )
