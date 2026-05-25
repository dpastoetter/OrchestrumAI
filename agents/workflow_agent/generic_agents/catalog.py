"""Catalog of toggleable generic sub-agents for General workflow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from .contract_clauses import build_contract_clauses_agent
from .doc_profile import build_doc_profile_agent
from .grep_doc import build_grep_doc_agent
from .editor import build_editor_agent
from .invoice_parser import build_invoice_parser_agent
from .pii_redactor import build_pii_redactor_agent
from .research import build_research_agent
from .table_peek import build_table_peek_agent
from .text_extract import build_text_extract_agent
from .writer import build_writer_agent

AgentCategory = Literal["private_doc", "writing", "web"]


@dataclass(frozen=True)
class GenericAgentDef:
    id: str
    name: str
    description: str
    default_enabled: bool
    build: Callable[[Any], Any]
    category: AgentCategory = "writing"


GENERIC_AGENT_CATALOG: tuple[GenericAgentDef, ...] = (
    GenericAgentDef(
        id="research",
        name="Research",
        description="Fetch and summarize URLs or long pasted context.",
        default_enabled=True,
        build=build_research_agent,
        category="web",
    ),
    GenericAgentDef(
        id="writer",
        name="Writer",
        description="Draft emails, summaries, and markdown from a brief.",
        default_enabled=True,
        build=build_writer_agent,
        category="writing",
    ),
    GenericAgentDef(
        id="editor",
        name="Editor",
        description="Review a draft and return concise feedback.",
        default_enabled=False,
        build=build_editor_agent,
        category="writing",
    ),
    GenericAgentDef(
        id="text_extract",
        name="Text Extractor",
        description="Read text from local PDF, txt, or md uploads (private).",
        default_enabled=False,
        build=build_text_extract_agent,
        category="private_doc",
    ),
    GenericAgentDef(
        id="table_peek",
        name="Table Peek",
        description="Preview CSV/XLSX/PDF tables locally without Sheets export.",
        default_enabled=False,
        build=build_table_peek_agent,
        category="private_doc",
    ),
    GenericAgentDef(
        id="pii_redactor",
        name="PII Redactor",
        description="Mask emails, phones, and addresses in local document text.",
        default_enabled=False,
        build=build_pii_redactor_agent,
        category="private_doc",
    ),
    GenericAgentDef(
        id="invoice_parser",
        name="Invoice Parser",
        description="Extract vendor, line items, and totals from invoices.",
        default_enabled=False,
        build=build_invoice_parser_agent,
        category="private_doc",
    ),
    GenericAgentDef(
        id="contract_clauses",
        name="Clause Finder",
        description="Find termination, payment, liability, and confidentiality clauses.",
        default_enabled=False,
        build=build_contract_clauses_agent,
        category="private_doc",
    ),
    GenericAgentDef(
        id="grep_doc",
        name="Grep Doc",
        description="Search keywords across uploaded local document text.",
        default_enabled=False,
        build=build_grep_doc_agent,
        category="private_doc",
    ),
    GenericAgentDef(
        id="doc_profile",
        name="Doc Profile",
        description="Summarize file type, size, OCR risk, and table/text preview.",
        default_enabled=False,
        build=build_doc_profile_agent,
        category="private_doc",
    ),
)

_CATALOG_BY_ID = {a.id: a for a in GENERIC_AGENT_CATALOG}
_VALID_IDS = frozenset(_CATALOG_BY_ID.keys())

_TOOL_NAMES: dict[str, str] = {
    "research": "research_agent",
    "writer": "writer_agent",
    "editor": "editor_agent",
    "text_extract": "text_extract_agent",
    "table_peek": "table_peek_agent",
    "pii_redactor": "pii_redactor_agent",
    "invoice_parser": "invoice_parser_agent",
    "contract_clauses": "contract_clauses_agent",
    "grep_doc": "grep_doc_agent",
    "doc_profile": "doc_profile_agent",
}


def tool_name_for(agent_id: str) -> str:
    return _TOOL_NAMES.get(agent_id, f"{agent_id}_agent")


def default_enabled_ids() -> list[str]:
    return [a.id for a in GENERIC_AGENT_CATALOG if a.default_enabled]


def resolve_enabled_ids(
    global_enabled: list[str] | None,
    request_override: list[str] | None,
) -> list[str]:
    """Merge global settings with per-request override."""
    if request_override is not None:
        source = request_override
    elif global_enabled is not None:
        source = global_enabled
    else:
        source = default_enabled_ids()
    return [aid for aid in source if aid in _VALID_IDS]


def get_catalog_for_api() -> list[dict[str, Any]]:
    return [
        {
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "default_enabled": a.default_enabled,
            "category": a.category,
        }
        for a in GENERIC_AGENT_CATALOG
    ]


def build_enabled_sub_agents(model: Any, enabled_ids: list[str]) -> list[Any]:
    """Build LlmAgent instances for enabled catalog entries."""
    agents = []
    for agent_id in enabled_ids:
        defn = _CATALOG_BY_ID.get(agent_id)
        if defn is not None:
            agents.append(defn.build(model))
    return agents


def delegate_instruction_section(enabled_ids: list[str]) -> str:
    if not enabled_ids:
        return (
            "\n\nNo specialist sub-agents are enabled for this request. "
            "Perform all work yourself during EXECUTING."
        )
    lines = [
        "\n\nEnabled specialist sub-agents (invoke via their AgentTool during EXECUTING only):"
    ]
    for agent_id in enabled_ids:
        defn = _CATALOG_BY_ID.get(agent_id)
        if defn:
            tool_name = tool_name_for(agent_id)
            lines.append(f"- {defn.name} (tool `{tool_name}`): {defn.description}")
    lines.append(
        "Delegate specialized tasks to these tools, then synthesize their output into "
        "result_summary before calling complete_request. Mention planned delegates in "
        "proposed_actions when requesting approval."
    )
    return "\n".join(lines)
