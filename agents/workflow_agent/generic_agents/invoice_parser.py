"""Invoice Parser: structured fields from invoice text."""

from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent

from .doc_tools import read_local_excerpt_tool

_INSTRUCTION = """You extract invoice fields from local document text only.

Call read_local_excerpt if the input implies an uploaded file. Use only values present
in the text; mark missing fields as null in JSON.

Return markdown with:
- Vendor, invoice number, dates, currency
- Line items table (description, qty, unit price, amount)
- Subtotal, tax, total

Then a JSON block with the same structure. If a field is not in the document, do not guess."""


def build_invoice_parser_agent(model: Any) -> LlmAgent:
    return LlmAgent(
        name="invoice_parser_agent",
        description="Parses vendor invoices from local PDF/text into tables and JSON.",
        instruction=_INSTRUCTION,
        model=model,
        tools=[read_local_excerpt_tool],
    )
