"""CRUD and run endpoints for saved workflow templates."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from fastapi.responses import JSONResponse

from .config import DEFAULT_USER_ID
from .models import (
    RunTemplateBody,
    SaveAsTemplateBody,
    WorkflowTemplateBody,
    WorkflowTemplateSummary,
)
from .request_format import parse_topology_from_record
from .request_service import create_request_from_template
from .request_store import RequestStore
from .runner_bridge import get_runner_bridge
from .template_store import TemplateStore, parse_json_field

router = APIRouter(tags=["workflow-templates"])

_template_store = TemplateStore()
_request_store = RequestStore()
_bridge = get_runner_bridge()


def _user_id(header: str | None) -> str:
    return (header or "").strip() or DEFAULT_USER_ID


def _template_to_summary(record) -> WorkflowTemplateSummary:
    topo = parse_json_field(record.agent_topology, None)
    return WorkflowTemplateSummary(
        id=record.id,
        user_id=record.user_id,
        name=record.name,
        description_template=record.description_template,
        agent_type=record.agent_type,
        agent_topology=topo if isinstance(topo, dict) else None,
        default_priority=record.default_priority,
        provider_id=record.provider_id,
        model_id=record.model_id,
        require_plan_approval=record.require_plan_approval,
        icon=record.icon,
        category=record.category,
        bundled=record.bundled,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _validate_topology_body(body: WorkflowTemplateBody) -> str:
    if body.agent_type == "workflow":
        if body.agent_topology is None:
            raise HTTPException(status_code=400, detail="workflow templates require agent_topology")
        from workflow_agent.topology import AgentTopology

        validated = AgentTopology.model_validate(
            body.agent_topology.model_dump(mode="json", by_alias=True)
        )
        return json.dumps(validated.to_dict())
    return ""


@router.get("/workflow-templates")
async def list_templates(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> dict[str, list[WorkflowTemplateSummary]]:
    user_id = _user_id(x_user_id)
    items = [_template_to_summary(t) for t in _template_store.list_templates(user_id)]
    return {"templates": items}


@router.post("/workflow-templates", status_code=201)
async def create_template(
    body: WorkflowTemplateBody,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> WorkflowTemplateSummary:
    user_id = _user_id(x_user_id)
    topo_json = _validate_topology_body(body)
    record = _template_store.create_template(
        user_id=user_id,
        name=body.name.strip(),
        description_template=body.description_template.strip(),
        agent_type=body.agent_type,
        agent_topology=topo_json,
        default_priority=body.default_priority,
        provider_id=body.provider_id.strip(),
        model_id=body.model_id.strip(),
        require_plan_approval=body.require_plan_approval,
        icon=body.icon.strip(),
        category=body.category.strip() or "general",
    )
    return _template_to_summary(record)


@router.get("/workflow-templates/{template_id}")
async def get_template(
    template_id: str,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> WorkflowTemplateSummary:
    record = _template_store.get_template(template_id)
    if record is None or record.user_id != _user_id(x_user_id):
        raise HTTPException(status_code=404, detail="Template not found")
    return _template_to_summary(record)


@router.put("/workflow-templates/{template_id}")
async def update_template(
    template_id: str,
    body: WorkflowTemplateBody,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> WorkflowTemplateSummary:
    record = _template_store.get_template(template_id)
    if record is None or record.user_id != _user_id(x_user_id):
        raise HTTPException(status_code=404, detail="Template not found")
    topo_json = _validate_topology_body(body)
    updated = _template_store.update_template(
        template_id,
        name=body.name.strip(),
        description_template=body.description_template.strip(),
        agent_type=body.agent_type,
        agent_topology=topo_json,
        default_priority=body.default_priority,
        provider_id=body.provider_id.strip(),
        model_id=body.model_id.strip(),
        require_plan_approval=body.require_plan_approval,
        icon=body.icon.strip(),
        category=body.category.strip() or "general",
    )
    return _template_to_summary(updated)


@router.delete("/workflow-templates/{template_id}", status_code=204)
async def delete_template(
    template_id: str,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> None:
    record = _template_store.get_template(template_id)
    if record is None or record.user_id != _user_id(x_user_id):
        raise HTTPException(status_code=404, detail="Template not found")
    for sched in _template_store.list_schedules_for_template(template_id):
        _template_store.delete_schedule(sched.id)
    _template_store.delete_template(template_id)


@router.post("/workflow-templates/{template_id}/run", status_code=202)
async def run_template(
    template_id: str,
    body: RunTemplateBody,
    background: BackgroundTasks,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    record = _template_store.get_template(template_id)
    if record is None or record.user_id != _user_id(x_user_id):
        raise HTTPException(status_code=404, detail="Template not found")
    summary = await create_request_from_template(
        background=background,
        bridge=_bridge,
        template=record,
        user_id=_user_id(x_user_id),
        title=body.title or None,
        description_vars=body.description_vars,
        run_source="template",
    )
    return summary


@router.get("/workflow-templates/{template_id}/export")
async def export_template(
    template_id: str,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> JSONResponse:
    record = _template_store.get_template(template_id)
    if record is None or record.user_id != _user_id(x_user_id):
        raise HTTPException(status_code=404, detail="Template not found")
    topo = parse_json_field(record.agent_topology, None)
    payload: dict[str, Any] = {
        "name": record.name,
        "description_template": record.description_template,
        "agent_type": record.agent_type,
        "agent_topology": topo,
        "default_priority": record.default_priority,
        "provider_id": record.provider_id,
        "model_id": record.model_id,
        "require_plan_approval": record.require_plan_approval,
        "icon": record.icon,
        "category": record.category,
    }
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="{record.name}.json"'},
    )


@router.post("/workflow-templates/import", status_code=201)
async def import_template(
    body: dict[str, Any],
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> WorkflowTemplateSummary:
    try:
        tpl_body = WorkflowTemplateBody.model_validate(body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return await create_template(tpl_body, x_user_id=x_user_id)


@router.post("/requests/{request_id}/save-as-template", status_code=201)
async def save_request_as_template(
    request_id: str,
    body: SaveAsTemplateBody,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> WorkflowTemplateSummary:
    user_id = _user_id(x_user_id)
    req = _request_store.get(request_id)
    if req is None or req.user_id != user_id:
        raise HTTPException(status_code=404, detail="Request not found")

    topo = parse_topology_from_record(req)
    if req.agent_type == "workflow" and not topo:
        raise HTTPException(status_code=400, detail="Request has no topology to save")

    desc_tpl = body.description_template.strip() or req.description
    record = _template_store.create_template(
        user_id=user_id,
        name=body.name.strip(),
        description_template=desc_tpl,
        agent_type=req.agent_type,
        agent_topology=json.dumps(topo) if topo else "",
        default_priority=req.priority,
        provider_id=req.llm_provider_id,
        model_id=req.llm_model_id,
        require_plan_approval=True,
        icon=body.icon.strip(),
        category=body.category.strip() or "general",
    )
    return _template_to_summary(record)
