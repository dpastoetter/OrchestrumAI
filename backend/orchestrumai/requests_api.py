"""REST API for workflow request submission and resume."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, Form, Header, HTTPException, UploadFile
from sse_starlette.sse import EventSourceResponse
from workflow_agent.state_schema import TERMINAL_STEPS, WorkflowStep

from .agents_registry import normalize_agent_type
from .config import DEFAULT_USER_ID
from .file_storage import delete_stored_file, save_upload
from .models import CreateRequestBody, RequestDetail, RequestSummary, ResumeRequestBody
from .request_events import append_event, clear_events, get_events, init_events
from .request_format import record_to_summary
from .request_service import create_request_impl, sync_record_from_session
from .request_store import RequestRecord, RequestStore
from .runner_bridge import get_runner_bridge

log = logging.getLogger(__name__)

router = APIRouter(tags=["requests"])

_store = RequestStore()
_bridge = get_runner_bridge()


def _user_id(header: str | None) -> str:
    return (header or "").strip() or DEFAULT_USER_ID


def _status_for_step(step: str) -> str:
    if step in TERMINAL_STEPS:
        return "done" if step == WorkflowStep.COMPLETED else "failed"
    if step == WorkflowStep.AWAITING_APPROVAL:
        return "awaiting_approval"
    return "active"


def _parse_state_json(state: dict[str, Any], key: str, default: Any) -> Any:
    raw = state.get(key)
    if raw is None or raw == "":
        return default
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default
    return raw


async def _sync_record_from_session(record: RequestRecord) -> RequestRecord:
    return await sync_record_from_session(record, _bridge)


def _detail_from_state(record: RequestRecord, state: dict[str, Any]) -> RequestDetail:
    preview_rows = _parse_state_json(state, "preview_rows_json", [])
    columns = _parse_state_json(state, "columns_json", [])
    column_mapping = _parse_state_json(state, "column_mapping_json", {})
    sheet_result = str(state.get("sheet_url", ""))
    summary = record_to_summary(record).model_dump()
    summary["llm_provider_id"] = str(state.get("llm_provider_id", summary.get("llm_provider_id", "")))
    summary["llm_model_id"] = str(state.get("llm_model_id", summary.get("llm_model_id", "")))
    summary["llm_display_name"] = str(state.get("llm_display_name", summary.get("llm_display_name", "")))
    return RequestDetail(
        **summary,
        proposed_actions=str(state.get("proposed_actions", "")),
        approval_summary=str(state.get("approval_summary", "")),
        plan_summary=str(state.get("plan_summary", "")),
        result_summary=str(state.get("result_summary", "")),
        error_message=str(state.get("error_message", "")),
        sheet_url=record.sheet_url,
        sheet_result_url=sheet_result,
        columns=columns if isinstance(columns, list) else [],
        preview_rows=preview_rows if isinstance(preview_rows, list) else [],
        column_mapping=column_mapping if isinstance(column_mapping, dict) else {},
        confidence_notes=str(state.get("confidence_notes", "")),
        rows_written=str(state.get("rows_written", "")),
        events=get_events(record.id),
    )


@router.get("/health")
async def health() -> dict[str, str | list[str]]:
    return {
        "status": "ok",
        "service": "orchestrumai",
        "features": [
            "agents",
            "providers",
            "workflow",
            "requests",
            "workflow-templates",
            "workflow-schedules",
            "automation",
        ],
    }


@router.get("/agents")
async def list_agents() -> list[dict[str, str]]:
    return [
        {"id": "workflow", "name": "General workflow", "description": "Plan, approve, execute any goal"},
        {
            "id": "doc_to_sheets",
            "name": "Document → Google Sheets",
            "description": "Upload PDF/CSV/XLSX, review extracted rows, export to Sheets",
        },
    ]


@router.post("/requests", status_code=202)
async def create_request_json(
    body: CreateRequestBody,
    background: BackgroundTasks,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> RequestSummary:
    return await create_request_impl(
        background=background,
        bridge=_bridge,
        user_id=_user_id(x_user_id),
        title=body.title,
        description=body.description,
        priority=body.priority,
        agent_type=body.agent_type,
        sheet_url=body.sheet_url,
        provider_id=body.provider_id,
        model_id=body.model_id,
        enabled_generic_agents=body.enabled_generic_agents,
        agent_topology=body.agent_topology,
        file_path="",
        file_name="",
        run_source="manual",
    )


@router.post("/requests/upload", status_code=202)
async def create_request_multipart(
    background: BackgroundTasks,
    title: str = Form(...),
    description: str = Form(...),
    priority: str = Form("normal"),
    agent_type: str = Form("doc_to_sheets"),
    sheet_url: str = Form(""),
    provider_id: str = Form(""),
    model_id: str = Form(""),
    agent_topology_json: str = Form(""),
    file: UploadFile = File(...),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> RequestSummary:
    if priority not in ("low", "normal", "high"):
        raise HTTPException(status_code=400, detail="Invalid priority")
    agent = normalize_agent_type(agent_type)
    if agent not in ("doc_to_sheets", "workflow"):
        raise HTTPException(
            status_code=400,
            detail="Multipart upload supports agent_type=workflow or doc_to_sheets",
        )
    try:
        file_path, file_name, mime = save_upload(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    topology_body: Any = None
    if agent == "workflow" and agent_topology_json.strip():
        from .models import AgentTopologyBody

        try:
            topology_body = AgentTopologyBody.model_validate_json(agent_topology_json)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid agent_topology: {exc}") from exc

    return await create_request_impl(
        background=background,
        bridge=_bridge,
        user_id=_user_id(x_user_id),
        title=title.strip(),
        description=description.strip(),
        priority=priority,
        agent_type=agent,
        sheet_url=sheet_url.strip(),
        provider_id=provider_id.strip(),
        model_id=model_id.strip(),
        agent_topology=topology_body,
        file_path=file_path,
        file_name=file_name,
        extra_state={"file_mime_type": mime},
        run_source="manual",
    )


@router.get("/requests")
async def list_requests(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> list[RequestSummary]:
    user_id = _user_id(x_user_id)
    synced: list[RequestSummary] = []
    for record in _store.list_for_user(user_id):
        record = await _sync_record_from_session(record)
        synced.append(record_to_summary(record))
    return synced


@router.delete("/requests/{request_id}", status_code=204)
async def delete_request(
    request_id: str,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> None:
    user_id = _user_id(x_user_id)
    record = _store.get(request_id)
    if record is None or record.user_id != user_id:
        raise HTTPException(status_code=404, detail="Request not found")
    try:
        await _bridge.delete_session(
            agent_type=record.agent_type,
            user_id=record.user_id,
            session_id=record.session_id,
        )
    except Exception:
        log.exception("Failed to delete ADK session for request %s", request_id)
    delete_stored_file(record.file_path)
    clear_events(request_id)
    if not _store.delete(request_id):
        raise HTTPException(status_code=404, detail="Request not found")


@router.get("/requests/{request_id}")
async def get_request(
    request_id: str,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> RequestDetail:
    user_id = _user_id(x_user_id)
    record = _store.get(request_id)
    if record is None or record.user_id != user_id:
        raise HTTPException(status_code=404, detail="Request not found")
    record = await _sync_record_from_session(record)
    state = await _bridge.get_session_state(
        agent_type=record.agent_type,
        user_id=record.user_id,
        session_id=record.session_id,
    )
    return _detail_from_state(record, state)


@router.post("/requests/{request_id}/resume")
async def resume_request(
    request_id: str,
    body: ResumeRequestBody,
    background: BackgroundTasks,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> RequestSummary:
    user_id = _user_id(x_user_id)
    record = _store.get(request_id)
    if record is None or record.user_id != user_id:
        raise HTTPException(status_code=404, detail="Request not found")
    record = await _sync_record_from_session(record)
    if record.current_step != WorkflowStep.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=409,
            detail=f"Request is not awaiting approval (current: {record.current_step})",
        )

    async def _resume_task() -> None:
        try:
            async for payload in _bridge.resume_request(
                agent_type=record.agent_type,
                user_id=record.user_id,
                session_id=record.session_id,
                decision=body.decision,
                comment=body.comment,
            ):
                append_event(request_id, payload.model_dump())
        except Exception as exc:
            log.exception("Resume failed for %s", request_id)
            append_event(
                request_id,
                {"kind": "error", "text": str(exc), "step": WorkflowStep.FAILED},
            )
        refreshed = _store.get(request_id)
        if refreshed:
            updated = await _sync_record_from_session(refreshed)
            append_event(
                request_id,
                {"kind": "status", "text": updated.status_message, "step": updated.current_step},
            )

    background.add_task(_resume_task)
    return record_to_summary(record)


@router.get("/requests/{request_id}/events")
async def request_events(
    request_id: str,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> EventSourceResponse:
    record = _store.get(request_id)
    if record is None or record.user_id != _user_id(x_user_id):
        raise HTTPException(status_code=404, detail="Request not found")

    async def generator():
        seen = 0
        for _ in range(120):
            buf = get_events(request_id)
            while seen < len(buf):
                yield {"event": "update", "data": json.dumps(buf[seen])}
                seen += 1
            refreshed = _store.get(request_id)
            if refreshed and refreshed.status in ("done", "failed"):
                yield {
                    "event": "done",
                    "data": json.dumps(
                        {"status": refreshed.status, "step": refreshed.current_step}
                    ),
                }
                return
            await asyncio.sleep(0.5)
        yield {"event": "timeout", "data": json.dumps({"message": "poll ended"})}

    return EventSourceResponse(generator())
