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
