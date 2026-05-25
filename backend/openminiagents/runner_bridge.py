"""ADK Runner wrapper for multiple agents."""

from __future__ import annotations

import json
import logging
import sys
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.runners import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.genai import types

from .agents_registry import app_name_for, load_agent_bundle, normalize_agent_type
from .config import AGENTS_DIR, STUB_RUN, session_service_uri
from .models import AgentEventPayload

log = logging.getLogger(__name__)

if str(AGENTS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(AGENTS_DIR.parent))


def _event_text(event: Any) -> str:
    if not event.content or not event.content.parts:
        return ""
    return "".join(p.text for p in event.content.parts if p.text).strip()


def _canonical_topology_key(topology: dict[str, Any] | None) -> str:
    if not topology:
        return ""
    return json.dumps(topology, sort_keys=True, separators=(",", ":"))


def _parse_agent_topology(state: dict[str, Any]) -> dict[str, Any] | None:
    raw = state.get("agent_topology")
    if raw is None or raw == "":
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _parse_enabled_generic_agents(state: dict[str, Any]) -> list[str]:
    raw = state.get("enabled_generic_agents")
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except json.JSONDecodeError:
            return []
    return []


def _event_to_payload(event: Any, step: str) -> AgentEventPayload:
    kind = "message"
    if event.get_function_calls():
        kind = "tool_call"
    elif event.get_function_responses():
        kind = "tool_response"
    return AgentEventPayload(
        kind=kind,
        text=_event_text(event),
        step=step,
        raw=event.model_dump(mode="json") if hasattr(event, "model_dump") else None,
    )


class RunnerBridge:
    """Manages ADK sessions and agent runs."""

    def __init__(self) -> None:
        self._session_service = DatabaseSessionService(db_url=session_service_uri())
        # cache key: app_name + provider_id + model_id
        self._runners: dict[str, Runner] = {}

    def clear_runner_cache(self) -> None:
        self._runners.clear()

    def _runner_key(
        self,
        agent_type: str,
        provider_id: str | None,
        model_id: str | None,
        enabled_generic_agents: list[str] | None = None,
        agent_topology: dict[str, Any] | None = None,
    ) -> str:
        if agent_topology is not None:
            topo = _canonical_topology_key(agent_topology)
            return f"{app_name_for(agent_type)}:{provider_id or ''}:{model_id or ''}:topo:{topo}"
        generic = ""
        if enabled_generic_agents is not None:
            generic = ",".join(sorted(enabled_generic_agents))
        return f"{app_name_for(agent_type)}:{provider_id or ''}:{model_id or ''}:{generic}"

    def _get_runner(
        self,
        agent_type: str,
        *,
        provider_id: str | None = None,
        model_id: str | None = None,
        enabled_generic_agents: list[str] | None = None,
        agent_topology: dict[str, Any] | None = None,
    ) -> Runner:
        app_name = app_name_for(agent_type)
        key = self._runner_key(
            agent_type,
            provider_id,
            model_id,
            enabled_generic_agents,
            agent_topology,
        )
        if key not in self._runners:
            root_agent, _, _ = load_agent_bundle(
                agent_type,
                provider_id=provider_id,
                model_id=model_id,
                enabled_generic_agents=enabled_generic_agents,
                agent_topology=agent_topology,
            )
            self._runners[key] = Runner(
                agent=root_agent,
                app_name=app_name,
                session_service=self._session_service,
                auto_create_session=False,
            )
        return self._runners[key]

    async def create_session(
        self,
        *,
        agent_type: str,
        user_id: str,
        title: str,
        description: str,
        priority: str,
        extra_state: dict[str, Any] | None = None,
        provider_id: str | None = None,
        model_id: str | None = None,
        enabled_generic_agents: list[str] | None = None,
        agent_topology: dict[str, Any] | None = None,
    ) -> str:
        _, initial_state, resolved = load_agent_bundle(
            agent_type,
            provider_id=provider_id,
            model_id=model_id,
            enabled_generic_agents=enabled_generic_agents,
            agent_topology=agent_topology,
        )
        state = {
            **initial_state,
            "request_title": title,
            "request_description": description,
            "request_priority": priority,
            "llm_provider_id": resolved.provider_id,
            "llm_model_id": resolved.model_id,
            "llm_display_name": resolved.display_name,
        }
        if extra_state:
            state.update(extra_state)
        session = await self._session_service.create_session(
            app_name=app_name_for(agent_type),
            user_id=user_id,
            state=state,
            session_id=str(uuid.uuid4()),
        )
        return session.id

    async def get_session_state(
        self,
        *,
        agent_type: str,
        user_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        session = await self._session_service.get_session(
            app_name=app_name_for(agent_type),
            user_id=user_id,
            session_id=session_id,
        )
        if session is None:
            return {}
        return dict(session.state or {})

    async def run_turn(
        self,
        *,
        agent_type: str,
        user_id: str,
        session_id: str,
        message: str,
        state_delta: dict[str, Any] | None = None,
        provider_id: str | None = None,
        model_id: str | None = None,
    ) -> AsyncGenerator[AgentEventPayload, None]:
        state = await self.get_session_state(
            agent_type=agent_type, user_id=user_id, session_id=session_id
        )
        pid = provider_id or state.get("llm_provider_id")
        mid = model_id or state.get("llm_model_id")
        enabled = _parse_enabled_generic_agents(state)
        topology = _parse_agent_topology(state)
        app_name = app_name_for(agent_type)
        if STUB_RUN and normalize_agent_type(agent_type) == "workflow":
            async for p in self._stub_workflow_turn(
                user_id=user_id,
                session_id=session_id,
                message=message,
                state_delta=state_delta,
                app_name=app_name,
            ):
                yield p
            return

        is_workflow = normalize_agent_type(agent_type) == "workflow"
        runner = self._get_runner(
            agent_type,
            provider_id=str(pid) if pid else None,
            model_id=str(mid) if mid else None,
            enabled_generic_agents=enabled if is_workflow and not topology else None,
            agent_topology=topology if is_workflow else None,
        )
        new_message = types.Content(role="user", parts=[types.Part(text=message)])
        step = "SUBMITTED"
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message,
            state_delta=state_delta,
        ):
            state = await self.get_session_state(
                agent_type=agent_type, user_id=user_id, session_id=session_id
            )
            step = str(state.get("current_step", step))
            yield _event_to_payload(event, step)

    async def start_request(
        self,
        *,
        agent_type: str,
        user_id: str,
        session_id: str,
        title: str,
        description: str,
        file_path: str | None = None,
        sheet_url: str | None = None,
        provider_id: str | None = None,
        model_id: str | None = None,
    ) -> None:
        normalized = normalize_agent_type(agent_type)
        if STUB_RUN and normalized == "workflow":
            await self._stub_workflow_initial(user_id=user_id, session_id=session_id)
            return
        if STUB_RUN and normalized == "doc_to_sheets":
            await self._stub_doc_to_sheets_initial(
                user_id=user_id,
                session_id=session_id,
                description=description,
                file_path=file_path or "",
            )
            return

        if normalized == "doc_to_sheets":
            prompt = (
                f"New document-to-sheets request.\nTitle: {title}\n"
                f"Description: {description}\n"
                f"File is at session state file_path. Target sheet: {sheet_url or 'default'}.\n"
                "Start from SUBMITTED: call parse_document first."
            )
        else:
            prompt = (
                f"A new request was submitted.\n\nTitle: {title}\n"
                f"Description: {description}\n\nBegin the workflow from SUBMITTED."
            )
        async for _ in self.run_turn(
            agent_type=agent_type,
            user_id=user_id,
            session_id=session_id,
            message=prompt,
            provider_id=provider_id,
            model_id=model_id,
        ):
            pass

    async def resume_request(
        self,
        *,
        agent_type: str,
        user_id: str,
        session_id: str,
        decision: str,
        comment: str = "",
    ) -> AsyncGenerator[AgentEventPayload, None]:
        from workflow_agent.state_schema import WorkflowStep

        app_name = app_name_for(agent_type)
        normalized = normalize_agent_type(agent_type)

        if STUB_RUN and normalized == "doc_to_sheets":
            async for p in self._stub_doc_to_sheets_resume(
                user_id=user_id,
                session_id=session_id,
                decision=decision,
                comment=comment,
                app_name=app_name,
            ):
                yield p
            return

        if STUB_RUN and normalized == "workflow":
            async for p in self._stub_workflow_resume(
                user_id=user_id,
                session_id=session_id,
                decision=decision,
                comment=comment,
                app_name=app_name,
            ):
                yield p
            return

        if decision == "approved":
            if normalized == "doc_to_sheets":
                message = (
                    "Human approved. Call append_rows_to_sheet, then complete_request "
                    "with the sheet URL."
                )
            else:
                message = (
                    "Human approval granted. Continue from AWAITING_APPROVAL: "
                    "call begin_execution, then complete_request when done."
                )
            state_delta = {"approval": "approved"}
            if comment:
                message += f"\nApprover comment: {comment}"
        else:
            message = "Human rejected. Call fail_request with the rejection reason."
            state_delta = {"approval": "rejected"}
            if comment:
                message += f"\nRejection reason: {comment}"

        state = await self.get_session_state(
            agent_type=agent_type, user_id=user_id, session_id=session_id
        )
        pid = state.get("llm_provider_id")
        mid = state.get("llm_model_id")
        async for payload in self.run_turn(
            agent_type=agent_type,
            user_id=user_id,
            session_id=session_id,
            message=message,
            state_delta=state_delta,
            provider_id=str(pid) if pid else None,
            model_id=str(mid) if mid else None,
        ):
            yield payload

    async def _apply_state(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        updates: dict[str, Any],
    ) -> None:
        session = await self._session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
        )
        if session is None:
            return
        await self._session_service.append_event(
            session=session,
            event=Event(
                author="system",
                content=types.Content(
                    role="user",
                    parts=[types.Part(text="[state update]")],
                ),
                actions=EventActions(state_delta=updates),
            ),
        )

    async def _stub_workflow_initial(self, *, user_id: str, session_id: str) -> None:
        from workflow_agent.state_schema import WorkflowStep

        app_name = app_name_for("workflow")
        state = await self.get_session_state(
            agent_type="workflow", user_id=user_id, session_id=session_id
        )
        enabled = _parse_enabled_generic_agents(state)
        topology = _parse_agent_topology(state)
        delegate_note = ""
        if topology:
            try:
                from workflow_agent.topology import AgentTopology

                topo = AgentTopology.model_validate(topology)
                labels = ", ".join(topo.summary_labels())
                delegate_note = (
                    f" Topology: {topo.type}."
                    f" Agents: {labels}."
                )
            except Exception:
                delegate_note = f" Topology: {topology.get('type', 'custom')}."
        elif enabled:
            delegate_note = f" Enabled specialists: {', '.join(enabled)}."
        await self._apply_state(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            updates={
                "current_step": WorkflowStep.PLANNING,
                "plan_summary": "Stub plan.",
                "status_message": "Planning (stub).",
            },
        )
        await self._apply_state(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            updates={
                "current_step": WorkflowStep.AWAITING_APPROVAL,
                "approval_summary": "Stub workflow ready for review.",
                "proposed_actions": f"1. Analyze\n2. Delegate to specialists\n3. Complete.{delegate_note}",
                "status_message": "Waiting for approval (stub).",
                "latest_output": "Plan ready.",
            },
        )

    async def _stub_workflow_resume(
        self,
        *,
        user_id: str,
        session_id: str,
        decision: str,
        comment: str,
        app_name: str,
    ) -> AsyncGenerator[AgentEventPayload, None]:
        from workflow_agent.state_schema import WorkflowStep

        if decision == "approved":
            await self._apply_state(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                updates={"current_step": WorkflowStep.EXECUTING, "status_message": "Executing (stub)."},
            )
            yield AgentEventPayload(kind="message", text="Executing (stub).", step=WorkflowStep.EXECUTING)
            result = f"Completed (stub). {comment}".strip() or "Done."
            await self._apply_state(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                updates={
                    "current_step": WorkflowStep.COMPLETED,
                    "result_summary": result,
                    "status_message": "Completed (stub).",
                    "latest_output": result,
                },
            )
            yield AgentEventPayload(kind="message", text=result, step=WorkflowStep.COMPLETED)
        else:
            err = comment or "Rejected."
            await self._apply_state(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                updates={
                    "current_step": WorkflowStep.FAILED,
                    "error_message": err,
                    "status_message": f"Failed: {err}",
                    "latest_output": err,
                },
            )
            yield AgentEventPayload(kind="message", text=err, step=WorkflowStep.FAILED)

    async def _stub_doc_to_sheets_initial(
        self,
        *,
        user_id: str,
        session_id: str,
        description: str,
        file_path: str,
    ) -> None:
        from workflow_agent.state_schema import WorkflowStep

        from .document_parser import default_column_mapping, extract_table
        from .sheets_client import parse_spreadsheet_id

        app_name = app_name_for("doc_to_sheets")
        state = await self.get_session_state(
            agent_type="doc_to_sheets", user_id=user_id, session_id=session_id
        )
        table = extract_table(
            file_path or "",
            description=description,
            stub=True,
            provider_id=str(state.get("llm_provider_id", "")) or None,
            model_id=str(state.get("llm_model_id", "")) or None,
        )
        rows = table["rows"]
        columns = table["columns"]
        mapping = default_column_mapping(columns)

        await self._apply_state(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            updates={
                "current_step": WorkflowStep.PLANNING,
                "status_message": f"Extracted {len(rows)} rows (stub).",
                "preview_rows_json": json.dumps(rows),
                "columns_json": json.dumps(columns),
                "column_mapping_json": json.dumps(mapping),
                "confidence_notes": table.get("confidence_notes", ""),
            },
        )
        await self._apply_state(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            updates={
                "current_step": WorkflowStep.AWAITING_APPROVAL,
                "approval_summary": f"Review {len(rows)} extracted rows before writing to Sheets.",
                "proposed_actions": "Approve to append rows to the target spreadsheet.",
                "status_message": "Waiting for approval.",
                "latest_output": f"{len(rows)} rows ready.",
            },
        )

    async def _stub_doc_to_sheets_resume(
        self,
        *,
        user_id: str,
        session_id: str,
        decision: str,
        comment: str,
        app_name: str,
    ) -> AsyncGenerator[AgentEventPayload, None]:
        from workflow_agent.state_schema import WorkflowStep

        from .config import DEFAULT_SPREADSHEET_ID
        from .sheets_client import append_rows, parse_spreadsheet_id

        if decision != "approved":
            err = comment or "Rejected by user."
            await self._apply_state(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                updates={
                    "current_step": WorkflowStep.FAILED,
                    "error_message": err,
                    "status_message": f"Failed: {err}",
                },
            )
            yield AgentEventPayload(kind="message", text=err, step=WorkflowStep.FAILED)
            return

        state = await self.get_session_state(
            agent_type="doc_to_sheets", user_id=user_id, session_id=session_id
        )
        rows = json.loads(str(state.get("preview_rows_json", "[]")))
        columns = json.loads(str(state.get("columns_json", "[]")))
        sheet_id = str(state.get("target_sheet_id") or DEFAULT_SPREADSHEET_ID or "stub-sheet-id")

        await self._apply_state(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            updates={"current_step": WorkflowStep.EXECUTING, "status_message": "Writing to Sheets (stub)."},
        )
        yield AgentEventPayload(kind="message", text="Writing rows…", step=WorkflowStep.EXECUTING)

        result = append_rows(parse_spreadsheet_id(sheet_id), rows, columns, stub=True)
        summary = (
            f"Wrote {result['rows_written']} rows. {result['sheet_url']}"
            + (f" Comment: {comment}" if comment else "")
        )
        await self._apply_state(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            updates={
                "current_step": WorkflowStep.COMPLETED,
                "sheet_url": result["sheet_url"],
                "rows_written": str(result["rows_written"]),
                "result_summary": summary,
                "status_message": "Export complete.",
                "latest_output": summary,
            },
        )
        yield AgentEventPayload(kind="message", text=summary, step=WorkflowStep.COMPLETED)

    async def _stub_workflow_turn(
        self,
        *,
        user_id: str,
        session_id: str,
        message: str,
        state_delta: dict[str, Any] | None,
        app_name: str,
    ) -> AsyncGenerator[AgentEventPayload, None]:
        if state_delta:
            await self._apply_state(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                updates=state_delta,
            )
        state = await self.get_session_state(
            agent_type="workflow", user_id=user_id, session_id=session_id
        )
        yield AgentEventPayload(
            kind="message",
            text=message,
            step=str(state.get("current_step", "SUBMITTED")),
        )


_bridge: RunnerBridge | None = None


def get_runner_bridge() -> RunnerBridge:
    global _bridge
    if _bridge is None:
        _bridge = RunnerBridge()
    return _bridge
