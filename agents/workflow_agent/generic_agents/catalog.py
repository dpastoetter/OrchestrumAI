"""Catalog of toggleable generic sub-agents for General workflow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .editor import build_editor_agent
from .research import build_research_agent
from .writer import build_writer_agent


@dataclass(frozen=True)
class GenericAgentDef:
    id: str
    name: str
    description: str
    default_enabled: bool
    build: Callable[[Any], Any]


GENERIC_AGENT_CATALOG: tuple[GenericAgentDef, ...] = (
    GenericAgentDef(
        id="research",
        name="Research",
        description="Fetch and summarize URLs or long pasted context.",
        default_enabled=True,
        build=build_research_agent,
    ),
    GenericAgentDef(
        id="writer",
        name="Writer",
        description="Draft emails, summaries, and markdown from a brief.",
        default_enabled=True,
        build=build_writer_agent,
    ),
    GenericAgentDef(
        id="editor",
        name="Editor",
        description="Review a draft and return concise feedback.",
        default_enabled=False,
        build=build_editor_agent,
    ),
)

_CATALOG_BY_ID = {a.id: a for a in GENERIC_AGENT_CATALOG}
_VALID_IDS = frozenset(_CATALOG_BY_ID.keys())


def default_enabled_ids() -> list[str]:
    return [a.id for a in GENERIC_AGENT_CATALOG if a.default_enabled]


def resolve_enabled_ids(
    global_enabled: list[str] | None,
    request_override: list[str] | None,
) -> list[str]:
    """Merge global settings with per-request override.

    If request_override is not None, use it exactly (may be empty).
    Otherwise use global_enabled or catalog defaults.
    """
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


_TOOL_NAMES = {
    "research": "research_agent",
    "writer": "writer_agent",
    "editor": "editor_agent",
}


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
            tool_name = _TOOL_NAMES.get(agent_id, agent_id)
            lines.append(f"- {defn.name} (tool `{tool_name}`): {defn.description}")
    lines.append(
        "Delegate specialized tasks to these tools, then synthesize their output into "
        "result_summary before calling complete_request. Mention planned delegates in "
        "proposed_actions when requesting approval."
    )
    return "\n".join(lines)
