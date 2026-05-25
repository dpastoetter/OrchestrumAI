"""CRUD and manual trigger for workflow schedules."""

from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException

from .config import DEFAULT_USER_ID
from .cron_utils import compute_next_run, validate_cron
from .models import WorkflowScheduleBody, WorkflowScheduleSummary
from .request_service import create_request_from_template
from .runner_bridge import get_runner_bridge
from .scheduler_service import get_scheduler_service
from .template_store import TemplateStore, parse_json_field

router = APIRouter(tags=["workflow-schedules"])

_store = TemplateStore()
_bridge = get_runner_bridge()


def _user_id(header: str | None) -> str:
    return (header or "").strip() or DEFAULT_USER_ID


def _schedule_summary(record, template_name: str = "") -> WorkflowScheduleSummary:
    return WorkflowScheduleSummary(
        id=record.id,
        user_id=record.user_id,
        template_id=record.template_id,
        template_name=template_name,
        cron_expression=record.cron_expression,
        timezone=record.timezone,
        enabled=record.enabled,
        description_vars=parse_json_field(record.description_vars, {}),
        on_approval=record.on_approval,
        last_run_at=record.last_run_at,
        next_run_at=record.next_run_at,
        last_request_id=record.last_request_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("/workflow-schedules")
async def list_schedules(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> dict[str, list[WorkflowScheduleSummary]]:
    user_id = _user_id(x_user_id)
    out: list[WorkflowScheduleSummary] = []
    for sched in _store.list_schedules(user_id):
        tpl = _store.get_template(sched.template_id)
        name = tpl.name if tpl else ""
        out.append(_schedule_summary(sched, name))
    return {"schedules": out}


@router.post("/workflow-schedules", status_code=201)
async def create_schedule(
    body: WorkflowScheduleBody,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> WorkflowScheduleSummary:
    user_id = _user_id(x_user_id)
    tpl = _store.get_template(body.template_id)
    if tpl is None or tpl.user_id != user_id:
        raise HTTPException(status_code=404, detail="Template not found")
    try:
        validate_cron(body.cron_expression)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    next_run = compute_next_run(body.cron_expression, body.timezone)
    record = _store.create_schedule(
        user_id=user_id,
        template_id=body.template_id,
        cron_expression=body.cron_expression.strip(),
        tz_name=body.timezone.strip() or "UTC",
        enabled=body.enabled,
        description_vars=json.dumps(body.description_vars),
        on_approval=body.on_approval,
        next_run_at=next_run,
    )
    get_scheduler_service().refresh()
    return _schedule_summary(record, tpl.name)


@router.put("/workflow-schedules/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    body: WorkflowScheduleBody,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> WorkflowScheduleSummary:
    record = _store.get_schedule(schedule_id)
    if record is None or record.user_id != _user_id(x_user_id):
        raise HTTPException(status_code=404, detail="Schedule not found")
    try:
        validate_cron(body.cron_expression)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    next_run = compute_next_run(body.cron_expression, body.timezone)
    updated = _store.update_schedule(
        schedule_id,
        template_id=body.template_id,
        cron_expression=body.cron_expression.strip(),
        tz_name=body.timezone.strip() or "UTC",
        enabled=body.enabled,
        description_vars=json.dumps(body.description_vars),
        on_approval=body.on_approval,
        next_run_at=next_run,
    )
    tpl = _store.get_template(body.template_id)
    get_scheduler_service().refresh()
    return _schedule_summary(updated, tpl.name if tpl else "")


@router.delete("/workflow-schedules/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: str,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> None:
    record = _store.get_schedule(schedule_id)
    if record is None or record.user_id != _user_id(x_user_id):
        raise HTTPException(status_code=404, detail="Schedule not found")
    _store.delete_schedule(schedule_id)
    get_scheduler_service().refresh()


@router.post("/workflow-schedules/{schedule_id}/trigger", status_code=202)
async def trigger_schedule(
    schedule_id: str,
    background: BackgroundTasks,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    user_id = _user_id(x_user_id)
    sched = _store.get_schedule(schedule_id)
    if sched is None or sched.user_id != user_id:
        raise HTTPException(status_code=404, detail="Schedule not found")
    tpl = _store.get_template(sched.template_id)
    if tpl is None:
        raise HTTPException(status_code=404, detail="Template not found")
    summary = await get_scheduler_service().run_schedule(
        sched,
        tpl,
        background=background,
        force=True,
    )
    if summary is None:
        raise HTTPException(
            status_code=409,
            detail="Previous scheduled run still active or awaiting approval",
        )
    return summary
