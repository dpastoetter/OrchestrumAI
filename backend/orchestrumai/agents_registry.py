"""Maps UI agent types to ADK app names and agent modules."""

from __future__ import annotations

from typing import Any

from .llm_providers import ResolvedModel, apply_litellm_env, build_adk_model

AGENT_TYPES = frozenset({"workflow", "doc_to_sheets"})

APP_NAMES: dict[str, str] = {
    "workflow": "workflow_agent",
    "doc_to_sheets": "doc_to_sheets_agent",
}


def normalize_agent_type(agent_type: str | None) -> str:
    if not agent_type or agent_type not in AGENT_TYPES:
        return "workflow"
    return agent_type


def app_name_for(agent_type: str) -> str:
    return APP_NAMES[normalize_agent_type(agent_type)]


def load_agent_bundle(
    agent_type: str,
    *,
    provider_id: str | None = None,
    model_id: str | None = None,
    enabled_generic_agents: list[str] | None = None,
    agent_topology: dict[str, Any] | None = None,
) -> tuple[Any, dict[str, Any], ResolvedModel]:
    """Return (root_agent, initial_state, resolved_model)."""
    apply_litellm_env()
    resolved = build_adk_model(provider_id or "", model_id)
    normalized = normalize_agent_type(agent_type)
    if normalized == "doc_to_sheets":
        from doc_to_sheets_agent.agent import INITIAL_STATE, build_agent

        return build_agent(resolved.adk_model), INITIAL_STATE, resolved
    from workflow_agent.agent import build_agent, build_initial_state

    if agent_topology is not None:
        return (
            build_agent(resolved.adk_model, topology=agent_topology),
            build_initial_state(topology=agent_topology),
            resolved,
        )
    enabled = enabled_generic_agents
    return (
        build_agent(resolved.adk_model, enabled),
        build_initial_state(enabled),
        resolved,
    )
