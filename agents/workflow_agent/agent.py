"""Root ADK agent for user-submitted workflow requests."""

from __future__ import annotations

import json
import os
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from .generic_agents.catalog import (
    GENERIC_AGENT_CATALOG,
    build_enabled_sub_agents,
    default_enabled_ids,
    delegate_instruction_section,
)
from .instructions import BASE_INSTRUCTION
from .state_schema import WorkflowStep
from .tools import WORKFLOW_TOOLS
from .topology import AgentTopology
from .topology_builder import build_agent_from_topology


def build_agent(
    model: Any | None = None,
    enabled_generic_ids: list[str] | None = None,
    topology: AgentTopology | dict[str, Any] | None = None,
) -> LlmAgent:
    resolved = model or os.environ.get("ADK_DEFAULT_MODEL", "gemini-2.5-flash")
    if topology is not None:
        topo = (
            topology
            if isinstance(topology, AgentTopology)
            else AgentTopology.model_validate(topology)
        )
        return build_agent_from_topology(resolved, topo)

    valid = {a.id for a in GENERIC_AGENT_CATALOG}
    if enabled_generic_ids is None:
        enabled = default_enabled_ids()
    else:
        enabled = [i for i in enabled_generic_ids if i in valid]

    sub_agents = build_enabled_sub_agents(resolved, enabled)
    delegate_tools = [AgentTool(agent) for agent in sub_agents]
    instruction = BASE_INSTRUCTION + delegate_instruction_section(enabled)

    return LlmAgent(
        name="workflow_agent",
        description="Processes submitted requests through plan, approval, execution, and completion.",
        instruction=instruction,
        model=resolved,
        tools=[*WORKFLOW_TOOLS, *delegate_tools],
    )


def build_initial_state(
    enabled_generic_ids: list[str] | None = None,
    topology: AgentTopology | dict[str, Any] | None = None,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "current_step": WorkflowStep.SUBMITTED,
        "status_message": "Request submitted.",
    }
    if topology is not None:
        topo = (
            topology
            if isinstance(topology, AgentTopology)
            else AgentTopology.model_validate(topology)
        )
        state["agent_topology"] = json.dumps(topo.to_dict())
        state["enabled_generic_agents"] = json.dumps([])
    else:
        enabled = enabled_generic_ids if enabled_generic_ids is not None else default_enabled_ids()
        state["enabled_generic_agents"] = json.dumps(enabled)
        state["agent_topology"] = ""
    return state


# Default export for ADK agent loader (catalog defaults)
root_agent = build_agent()
INITIAL_STATE = build_initial_state()
