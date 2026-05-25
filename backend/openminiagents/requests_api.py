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
from .file_storage import save_upload
from .models import CreateRequestBody, RequestDetail, RequestSummary, ResumeRequestBody
from .request_store import RequestRecord, RequestStore
from .runner_bridge import get_runner_bridge
from .sheets_client import parse_spreadsheet_id

log = logging.getLogger(__name__)

router = APIRouter(tags=["requests"])

_store = RequestStore()
_bridge = get_runner_bridge()

_event_buffers: dict[str, list[dict[str, Any]]] = {}


def _user_id(header: str | None) -> str:
    return (header or "").strip() or DEFAULT_USER_ID


def _status_for_step(step: str) -> str:
    if step in TERMINAL_STEPS:
        return "done" if step == WorkflowStep.COMPLETED else "failed"
    if step == WorkflowStep.AWAITING_APPROVAL:
        return "awaiting_approval"
    return "active"


def _parse_topology_from_record(record: RequestRecord) -> dict[str, Any] | None:
    raw = getattr(record, "agent_topology", None) or ""
    if not raw:
        return None
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def _topology_summary_fields(record: RequestRecord) -> dict[str, Any]:
    topo = _parse_topology_from_record(record)
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


def _parse_enabled_from_record(record: RequestRecord) -> list[str]:
    raw = getattr(record, "enabled_generic_agents", None) or "[]"
    if isinstance(raw, list):
        return [str(x) for x in raw]
    try:
        parsed = json.loads(raw)
        return [str(x) for x in parsed] if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


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


def _record_to_summary(record: RequestRecord) -> RequestSummary:
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
        enabled_generic_agents=_parse_enabled_from_record(record),
        **_topology_summary_fields(record),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


async def _sync_record_from_session(record: RequestRecord) -> RequestRecord:
    state = await _bridge.get_session_state(
        agent_type=record.agent_type,
        user_id=record.user_id,
        session_id=record.session_id,
    )
    step = str(state.get("current_step", record.current_step))
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
        status=_status_for_step(step),
    )
    return updated or record


def _append_event(request_id: str, payload: dict[str, Any]) -> None:
    buf = _event_buffers.setdefault(request_id, [])
    buf.append(payload)
    if len(buf) > 200:
        del buf[:-200]


async def _background_start(record: RequestRecord) -> None:
    try:
        await _bridge.start_request(
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
        updated = await _sync_record_from_session(record)
        _append_event(
            record.id,
            {"kind": "status", "text": updated.status_message, "step": updated.current_step},
        )
    except Exception as exc:
        log.exception("Agent start failed for %s", record.id)
        _store.update_from_session_state(
            record.id,
            current_step=WorkflowStep.FAILED,
            status_message=str(exc),
            latest_output=str(exc),
            status="failed",
        )
        _append_event(
            record.id,
            {"kind": "error", "text": str(exc), "step": WorkflowStep.FAILED},
        )


def _detail_from_state(record: RequestRecord, state: dict[str, Any]) -> RequestDetail:
    preview_rows = _parse_state_json(state, "preview_rows_json", [])
    columns = _parse_state_json(state, "columns_json", [])
    column_mapping = _parse_state_json(state, "column_mapping_json", {})
    sheet_result = str(state.get("sheet_url", ""))
    summary = _record_to_summary(record).model_dump()
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
        events=_event_buffers.get(record.id, []),
    )


@router.get("/health")
async def health() -> dict[str, str | list[str]]:
    return {
        "status": "ok",
        "service": "openminiagents",
        "features": ["agents", "providers", "workflow", "requests"],
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
    return await _create_request_impl(
        background=background,
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
    file: UploadFile = File(...),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> RequestSummary:
    if priority not in ("low", "normal", "high"):
        raise HTTPException(status_code=400, detail="Invalid priority")
    agent = normalize_agent_type(agent_type)
    if agent != "doc_to_sheets":
        raise HTTPException(status_code=400, detail="Multipart upload requires agent_type=doc_to_sheets")
    try:
        file_path, file_name, mime = save_upload(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _create_request_impl(
        background=background,
        user_id=_user_id(x_user_id),
        title=title.strip(),
        description=description.strip(),
        priority=priority,
        agent_type=agent,
        sheet_url=sheet_url.strip(),
        provider_id=provider_id.strip(),
        model_id=model_id.strip(),
        file_path=file_path,
        file_name=file_name,
        extra_state={"file_mime_type": mime},
    )


async def _create_request_impl(
    *,
    background: BackgroundTasks,
    user_id: str,
    title: str,
    description: str,
    priority: str,
    agent_type: str,
    sheet_url: str,
    provider_id: str = "",
    model_id: str = "",
    enabled_generic_agents: list[str] | None = None,
    agent_topology: Any = None,
    file_path: str = "",
    file_name: str = "",
    extra_state: dict[str, Any] | None = None,
) -> RequestSummary:
    agent = normalize_agent_type(agent_type)
    if agent == "doc_to_sheets" and not file_path:
        raise HTTPException(status_code=400, detail="doc_to_sheets requires a file upload")

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

    from .agents_registry import load_agent_bundle

    _, _, resolved = load_agent_bundle(
        agent,
        provider_id=provider_id or None,
        model_id=model_id or None,
        enabled_generic_agents=resolved_enabled if agent == "workflow" and not topology_dict else None,
        agent_topology=topology_dict if agent == "workflow" else None,
    )

    session_id = await _bridge.create_session(
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
    )
    _event_buffers[record.id] = []
    background.add_task(_background_start, record)
    return _record_to_summary(record)


@router.get("/requests")
async def list_requests(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> list[RequestSummary]:
    user_id = _user_id(x_user_id)
    synced: list[RequestSummary] = []
    for record in _store.list_for_user(user_id):
        record = await _sync_record_from_session(record)
        synced.append(_record_to_summary(record))
    return synced


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
                _append_event(request_id, payload.model_dump())
        except Exception as exc:
            log.exception("Resume failed for %s", request_id)
            _append_event(
                request_id,
                {"kind": "error", "text": str(exc), "step": WorkflowStep.FAILED},
            )
        refreshed = _store.get(request_id)
        if refreshed:
            updated = await _sync_record_from_session(refreshed)
            _append_event(
                request_id,
                {"kind": "status", "text": updated.status_message, "step": updated.current_step},
            )

    background.add_task(_resume_task)
    return _record_to_summary(record)


@router.get("/requests/{request_id}/events")
async def request_events(request_id: str) -> EventSourceResponse:
    record = _store.get(request_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Request not found")

    async def generator():
        seen = 0
        for _ in range(120):
            buf = _event_buffers.get(request_id, [])
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
