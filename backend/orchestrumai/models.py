"""Pydantic models for the public API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentType = Literal["workflow", "doc_to_sheets"]
Priority = Literal["low", "normal", "high"]
TopologyType = Literal["simple", "sequential", "orchestrator"]


class TopologyEdgeBody(BaseModel):
    from_: str = Field(alias="from")
    to: str

    model_config = {"populate_by_name": True}


class TopologyNodeBody(BaseModel):
    id: str
    kind: Literal["catalog", "custom"]
    catalog_id: str | None = None
    name: str = ""
    instruction: str = ""


class AgentTopologyBody(BaseModel):
    type: TopologyType
    nodes: list[TopologyNodeBody] = Field(default_factory=list)
    edges: list[TopologyEdgeBody] = Field(default_factory=list)


class CreateRequestBody(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=8000)
    priority: Priority = "normal"
    agent_type: AgentType = "workflow"
    sheet_url: str = ""
    provider_id: str = ""
    model_id: str = ""
    # None = use Settings defaults; [] = no sub-agents; non-empty = override
    enabled_generic_agents: list[str] | None = None
    agent_topology: AgentTopologyBody | None = None


class ResumeRequestBody(BaseModel):
    decision: Literal["approved", "rejected"]
    comment: str = ""


class WorkflowTemplateBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description_template: str = Field(min_length=1, max_length=8000)
    agent_type: AgentType = "workflow"
    agent_topology: AgentTopologyBody | None = None
    default_priority: Priority = "normal"
    provider_id: str = ""
    model_id: str = ""
    require_plan_approval: bool = True
    icon: str = Field(default="", max_length=16)
    category: str = Field(default="general", max_length=32)


class RunTemplateBody(BaseModel):
    title: str = ""
    description_vars: dict[str, Any] = Field(default_factory=dict)


class SaveAsTemplateBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description_template: str = ""
    icon: str = ""
    category: str = "general"


class WorkflowScheduleBody(BaseModel):
    template_id: str
    cron_expression: str = Field(min_length=9, max_length=128)
    timezone: str = "UTC"
    enabled: bool = True
    description_vars: dict[str, Any] = Field(default_factory=dict)
    on_approval: Literal["pause", "skip_plan"] = "pause"


class PreviewRow(BaseModel):
    data: dict[str, str] = Field(default_factory=dict)


class RequestSummary(BaseModel):
    id: str
    user_id: str
    session_id: str
    agent_type: str
    llm_provider_id: str = ""
    llm_model_id: str = ""
    llm_display_name: str = ""
    title: str
    description: str
    priority: str
    file_name: str = ""
    current_step: str
    status: str
    status_message: str
    latest_output: str = ""
    enabled_generic_agents: list[str] = Field(default_factory=list)
    agent_topology_type: str = ""
    agent_topology_labels: list[str] = Field(default_factory=list)
    workflow_template_id: str = ""
    workflow_schedule_id: str = ""
    run_source: str = ""
    created_at: datetime
    updated_at: datetime


class WorkflowTemplateSummary(BaseModel):
    id: str
    user_id: str
    name: str
    description_template: str
    agent_type: str
    agent_topology: dict[str, Any] | None = None
    default_priority: str
    provider_id: str = ""
    model_id: str = ""
    require_plan_approval: bool = True
    icon: str = ""
    category: str = "general"
    bundled: bool = False
    created_at: datetime
    updated_at: datetime


class WorkflowScheduleSummary(BaseModel):
    id: str
    user_id: str
    template_id: str
    template_name: str = ""
    cron_expression: str
    timezone: str
    enabled: bool
    description_vars: dict[str, Any] = Field(default_factory=dict)
    on_approval: str
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    last_request_id: str = ""
    created_at: datetime
    updated_at: datetime


class RequestDetail(RequestSummary):
    proposed_actions: str = ""
    approval_summary: str = ""
    plan_summary: str = ""
    result_summary: str = ""
    error_message: str = ""
    sheet_url: str = ""
    sheet_result_url: str = ""
    columns: list[str] = Field(default_factory=list)
    preview_rows: list[dict[str, Any]] = Field(default_factory=list)
    column_mapping: dict[str, str] = Field(default_factory=dict)
    confidence_notes: str = ""
    rows_written: str = ""
    events: list[dict[str, Any]] = Field(default_factory=list)


class AgentEventPayload(BaseModel):
    kind: str
    text: str = ""
    step: str = ""
    raw: dict[str, Any] | None = None
