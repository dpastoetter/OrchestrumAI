"""Build ADK workflow root agent from per-request topology."""

from __future__ import annotations

import re
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.tools.agent_tool import AgentTool

from .instructions import BASE_INSTRUCTION
from .generic_agents.catalog import _CATALOG_BY_ID, tool_name_for
from .tools import WORKFLOW_TOOLS
from .topology import AgentTopology, TopologyNode

_RE_SLUG = re.compile(r"[^a-z0-9_]+")


def _slug(name: str) -> str:
    s = _RE_SLUG.sub("_", name.lower().strip())[:48].strip("_")
    return s or "custom_agent"


def build_node_agent(model: Any, node: TopologyNode) -> LlmAgent:
    if node.kind == "catalog":
        defn = _CATALOG_BY_ID[node.catalog_id or ""]
        if defn is None:
            raise ValueError(f"Unknown catalog agent: {node.catalog_id}")
        return defn.build(model)
    return LlmAgent(
        name=_slug(node.name),
        description=node.name.strip(),
        instruction=node.instruction.strip(),
        model=model,
        tools=[],
    )


def _simple_role_section(node: TopologyNode) -> str:
    if node.kind == "catalog":
        defn = _CATALOG_BY_ID.get(node.catalog_id or "")
        if defn:
            return (
                f"\n\nYou also act as the {defn.name} specialist: {defn.description} "
                "Perform this role yourself during EXECUTING (no delegate tools)."
            )
        return ""
    return (
        f"\n\nYou also follow this specialist role ({node.name.strip()}):\n"
        f"{node.instruction.strip()}\n"
        "Perform this role yourself during EXECUTING."
    )


def _sequential_instruction_section(topology: AgentTopology) -> str:
    ordered = topology.ordered_nodes()
    lines = [
        "\n\nSequential pipeline (invoke tool `pipeline` during EXECUTING only):",
        "Runs sub-agents in this order; pass the user's goal as input.",
    ]
    for i, n in enumerate(ordered, 1):
        label = _node_label(n)
        lines.append(f"{i}. {label}")
    lines.append(
        "Call the pipeline tool once with the work brief, then synthesize the combined "
        "output into result_summary before complete_request."
    )
    return "\n".join(lines)


def _orchestrator_instruction_section(topology: AgentTopology) -> str:
    lines = [
        "\n\nOrchestrator delegates (invoke via AgentTool during EXECUTING only):",
    ]
    for n in topology.nodes:
        label = _node_label(n)
        if n.kind == "catalog":
            defn = _CATALOG_BY_ID.get(n.catalog_id or "")
            desc = defn.description if defn else ""
            tool_name = tool_name_for(n.catalog_id or "")
            lines.append(f"- {label} (tool `{tool_name}`): {desc}")
        else:
            slug = _slug(n.name)
            lines.append(f"- {label} (tool `{slug}`): {n.instruction.strip()[:200]}")
    lines.append(
        "Delegate specialized tasks, synthesize outputs into result_summary, then "
        "complete_request. Mention planned delegates in proposed_actions when requesting approval."
    )
    return "\n".join(lines)


def _node_label(node: TopologyNode) -> str:
    if node.kind == "catalog":
        defn = _CATALOG_BY_ID.get(node.catalog_id or "")
        return defn.name if defn else (node.catalog_id or "Agent")
    return node.name.strip() or "Custom"


def _simple_extra_tools(node: TopologyNode, model: Any) -> list[Any]:
    if node.kind != "catalog" or not node.catalog_id:
        return []
    built = build_node_agent(model, node)
    return list(built.tools or [])


def build_agent_from_topology(model: Any, topology: AgentTopology) -> LlmAgent:
    topology = AgentTopology.model_validate(topology.model_dump())

    if topology.type == "simple":
        node = topology.nodes[0]
        instruction = BASE_INSTRUCTION + _simple_role_section(node)
        return LlmAgent(
            name="workflow_agent",
            description="Single-agent workflow with plan, approval, and execution.",
            instruction=instruction,
            model=model,
            tools=[*WORKFLOW_TOOLS, *_simple_extra_tools(node, model)],
        )

    if topology.type == "sequential":
        ordered = topology.ordered_nodes()
        sub_agents = [build_node_agent(model, n) for n in ordered]
        pipeline = SequentialAgent(
            name="pipeline",
            description=(
                "Runs specialist agents in sequence. Input: brief describing the work. "
                "Output: combined results from each step."
            ),
            sub_agents=sub_agents,
        )
        instruction = BASE_INSTRUCTION + _sequential_instruction_section(topology)
        return LlmAgent(
            name="workflow_agent",
            description="Workflow coordinator with sequential specialist pipeline.",
            instruction=instruction,
            model=model,
            tools=[*WORKFLOW_TOOLS, AgentTool(pipeline)],
        )

    # orchestrator
    delegate_tools = [AgentTool(build_node_agent(model, n)) for n in topology.nodes]
    instruction = BASE_INSTRUCTION + _orchestrator_instruction_section(topology)
    return LlmAgent(
        name="workflow_agent",
        description="Workflow orchestrator delegating to specialist agents.",
        instruction=instruction,
        model=model,
        tools=[*WORKFLOW_TOOLS, *delegate_tools],
    )
