"""Shared request creation for API, templates, and scheduler."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import BackgroundTasks, HTTPException
from workflow_agent.state_schema import WorkflowStep

from .agents_registry import load_agent_bundle, normalize_agent_type
from .description_template import render_description_template
from .models import AgentTopologyBody, RequestSummary
from .request_store import RequestRecord, RequestStore
from .runner_bridge import RunnerBridge
from .sheets_client import parse_spreadsheet_id
from .template_store import WorkflowTemplateRecord, parse_json_field

log = logging.getLogger(__name__)

_store = RequestStore()


def get_request_store() -> RequestStore:
    return _store


async def sync_record_from_session(record: RequestRecord, bridge: RunnerBridge) -> RequestRecord:
    from workflow_agent.state_schema import TERMINAL_STEPS

    state = await bridge.get_session_state(
        agent_type=record.agent_type,
        user_id=record.user_id,
        session_id=record.session_id,
    )
    step = str(state.get("current_step", record.current_step))

    def status_for_step(s: str) -> str:
        if s in TERMINAL_STEPS:
            return "done" if s == WorkflowStep.COMPLETED else "failed"
        if s == WorkflowStep.AWAITING_APPROVAL:
            return "awaiting_approval"
        return "active"

    updated = _store.update_from_session_state(
        record.id,
        current_step=step,
        status_message=str(state.get("status_message", record.status_message)),
        latest_output=str(
            state.get("latest_output")
            or state.get("result_summary")
            or state.get("approval_summary")
            or record.latest_output
        ),
        status=status_for_step(step),
    )
    result = updated or record
    from .automation_hooks import on_request_status_change

    on_request_status_change(result)
    return result


def _schedule_auto_approve_plan(record: RequestRecord) -> bool:
    if not record.workflow_schedule_id:
        return False
    from .template_store import TemplateStore

    sched = TemplateStore().get_schedule(record.workflow_schedule_id)
    return sched is not None and sched.on_approval == "skip_plan"


async def _maybe_auto_approve_plan(
    record: RequestRecord, bridge: RunnerBridge
) -> RequestRecord:
    if record.status != "awaiting_approval":
        return record
    if not _schedule_auto_approve_plan(record):
        return record
    log.info("Auto-approving plan for scheduled request %s (skip_plan)", record.id)
    async for _ in bridge.resume_request(
        agent_type=record.agent_type,
        user_id=record.user_id,
        session_id=record.session_id,
        decision="approved",
        comment="Auto-approved (schedule policy: skip_plan)",
    ):
        pass
    return await sync_record_from_session(record, bridge)


async def background_start(record: RequestRecord, bridge: RunnerBridge) -> None:
    from .request_events import append_event

    try:
        await bridge.start_request(
            agent_type=record.agent_type,
            user_id=record.user_id,
            session_id=record.session_id,
            title=record.title,
            description=record.description,
            file_path=record.file_path or None,
            sheet_url=record.sheet_url or None,
            provider_id=record.llm_provider_id or None,
            model_id=record.llm_model_id or None,
        )
        updated = await sync_record_from_session(record, bridge)
        updated = await _maybe_auto_approve_plan(updated, bridge)
        append_event(
            record.id,
            {"kind": "status", "text": updated.status_message, "step": updated.current_step},
        )
        from .automation_hooks import on_request_status_change

        on_request_status_change(updated)
    except Exception as exc:
        log.exception("Agent start failed for %s", record.id)
        _store.update_from_session_state(
            record.id,
            current_step=WorkflowStep.FAILED,
            status_message=str(exc),
            latest_output=str(exc),
            status="failed",
        )
        append_event(
            record.id,
            {"kind": "error", "text": str(exc), "step": WorkflowStep.FAILED},
        )


async def create_request_impl(
    *,
    background: BackgroundTasks,
    bridge: RunnerBridge,
    user_id: str,
    title: str,
    description: str,
    priority: str,
    agent_type: str,
    sheet_url: str = "",
    provider_id: str = "",
    model_id: str = "",
    enabled_generic_agents: list[str] | None = None,
    agent_topology: Any = None,
    file_path: str = "",
    file_name: str = "",
    extra_state: dict[str, Any] | None = None,
    workflow_template_id: str = "",
    workflow_schedule_id: str = "",
    run_source: str = "",
) -> RequestSummary:
    from .request_events import init_events
    from .request_format import record_to_summary

    agent = normalize_agent_type(agent_type)
    if agent == "doc_to_sheets" and not file_path:
        raise HTTPException(
            status_code=400,
            detail="doc_to_sheets requires a file upload",
        )

    resolved_enabled: list[str] = []
    topology_dict: dict[str, Any] | None = None
    if agent == "workflow":
        if agent_topology is not None:
            from workflow_agent.topology import AgentTopology

            try:
                if hasattr(agent_topology, "model_dump"):
                    raw = agent_topology.model_dump(mode="json", by_alias=True)
                elif isinstance(agent_topology, dict):
                    raw = agent_topology
                else:
                    raise ValueError("Invalid topology payload")
                validated = AgentTopology.model_validate(raw)
                topology_dict = validated.to_dict()
            except Exception as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        else:
            from .workflow_settings import resolve_enabled_for_request

            resolved_enabled = resolve_enabled_for_request(enabled_generic_agents)

    session_extra: dict[str, Any] = dict(extra_state or {})
    if file_path:
        session_extra["file_path"] = file_path
        session_extra["file_name"] = file_name
    if sheet_url:
        session_extra["target_sheet_id"] = parse_spreadsheet_id(sheet_url)
        session_extra["sheet_url_input"] = sheet_url
    if workflow_template_id:
        session_extra["workflow_template_id"] = workflow_template_id
    if workflow_schedule_id:
        session_extra["workflow_schedule_id"] = workflow_schedule_id
    if run_source:
        session_extra["run_source"] = run_source

    _, _, resolved = load_agent_bundle(
        agent,
        provider_id=provider_id or None,
        model_id=model_id or None,
        enabled_generic_agents=resolved_enabled if agent == "workflow" and not topology_dict else None,
        agent_topology=topology_dict if agent == "workflow" else None,
    )

    session_id = await bridge.create_session(
        agent_type=agent,
        user_id=user_id,
        title=title,
        description=description,
        priority=priority,
        extra_state=session_extra,
        provider_id=provider_id or None,
        model_id=model_id or None,
        enabled_generic_agents=resolved_enabled if agent == "workflow" and not topology_dict else None,
        agent_topology=topology_dict if agent == "workflow" else None,
    )
    record = _store.create(
        user_id=user_id,
        session_id=session_id,
        title=title,
        description=description,
        priority=priority,
        agent_type=agent,
        file_path=file_path,
        file_name=file_name,
        sheet_url=sheet_url,
        llm_provider_id=resolved.provider_id,
        llm_model_id=resolved.model_id,
        llm_display_name=resolved.display_name,
        enabled_generic_agents=json.dumps(resolved_enabled),
        agent_topology=json.dumps(topology_dict) if topology_dict else "",
        status_message="Document uploaded." if agent == "doc_to_sheets" else "Request submitted.",
        workflow_template_id=workflow_template_id,
        workflow_schedule_id=workflow_schedule_id,
        run_source=run_source,
    )
    init_events(record.id)
    background.add_task(background_start, record, bridge)
    return record_to_summary(record)


async def create_request_from_template(
    *,
    background: BackgroundTasks,
    bridge: RunnerBridge,
    template: WorkflowTemplateRecord,
    user_id: str,
    title: str | None = None,
    description_vars: dict[str, Any] | None = None,
    workflow_schedule_id: str = "",
    run_source: str = "template",
) -> RequestSummary:
    description = render_description_template(
        template.description_template,
        vars=description_vars,
    )
    run_title = (title or "").strip() or template.name

    topology_body: AgentTopologyBody | None = None
    topo_raw = parse_json_field(template.agent_topology, None)
    if template.agent_type == "workflow" and isinstance(topo_raw, dict):
        topology_body = AgentTopologyBody.model_validate(topo_raw)

    if template.agent_type == "doc_to_sheets":
        raise HTTPException(
            status_code=400,
            detail="doc_to_sheets templates require a file; run from Submit with a template selected",
        )

    return await create_request_impl(
        background=background,
        bridge=bridge,
        user_id=user_id,
        title=run_title,
        description=description,
        priority=template.default_priority,
        agent_type=template.agent_type,
        provider_id=template.provider_id,
        model_id=template.model_id,
        agent_topology=topology_body,
        workflow_template_id=template.id,
        workflow_schedule_id=workflow_schedule_id,
        run_source=run_source or "template",
    )
