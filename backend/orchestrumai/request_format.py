"""Map RequestRecord to API summary models."""

from __future__ import annotations

import json
from typing import Any

from .models import RequestSummary
from .request_store import RequestRecord


def parse_topology_from_record(record: RequestRecord) -> dict[str, Any] | None:
    raw = getattr(record, "agent_topology", None) or ""
    if not raw:
        return None
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def topology_summary_fields(record: RequestRecord) -> dict[str, Any]:
    topo = parse_topology_from_record(record)
    if not topo:
        return {"agent_topology_type": "", "agent_topology_labels": []}
    try:
        from workflow_agent.topology import AgentTopology

        validated = AgentTopology.model_validate(topo)
        return {
            "agent_topology_type": validated.type,
            "agent_topology_labels": validated.summary_labels(),
        }
    except Exception:
        return {
            "agent_topology_type": str(topo.get("type", "")),
            "agent_topology_labels": [],
        }


def parse_enabled_from_record(record: RequestRecord) -> list[str]:
    raw = getattr(record, "enabled_generic_agents", None) or "[]"
    if isinstance(raw, list):
        return [str(x) for x in raw]
    try:
        parsed = json.loads(raw)
        return [str(x) for x in parsed] if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def record_to_summary(record: RequestRecord) -> RequestSummary:
    return RequestSummary(
        id=record.id,
        user_id=record.user_id,
        session_id=record.session_id,
        agent_type=record.agent_type,
        llm_provider_id=record.llm_provider_id,
        llm_model_id=record.llm_model_id,
        llm_display_name=record.llm_display_name,
        title=record.title,
        description=record.description,
        priority=record.priority,
        file_name=record.file_name,
        current_step=record.current_step,
        status=record.status,
        status_message=record.status_message,
        latest_output=record.latest_output,
        enabled_generic_agents=parse_enabled_from_record(record),
        workflow_template_id=getattr(record, "workflow_template_id", "") or "",
        workflow_schedule_id=getattr(record, "workflow_schedule_id", "") or "",
        run_source=getattr(record, "run_source", "") or "",
        **topology_summary_fields(record),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
