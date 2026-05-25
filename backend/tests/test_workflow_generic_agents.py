"""Tests for toggleable generic workflow sub-agents."""

from __future__ import annotations

import json
import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ["ORCHESTRUMAI_STUB_RUN"] = "1"
os.environ["ORCHESTRUMAI_DATA_DIR"] = "/tmp/orchestrumai-wf-generic-test"

from orchestrumai.app import create_app
from orchestrumai.workflow_settings import (
    get_workflow_settings,
    resolve_enabled_for_request,
    update_workflow_settings,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def reset_workflow_settings():
    update_workflow_settings(enabled_generic_agents=["research", "writer"])
    yield


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def test_catalog_lists_agents():
    from workflow_agent.generic_agents.catalog import GENERIC_AGENT_CATALOG

    assert len(GENERIC_AGENT_CATALOG) >= 8
    ids = {a.id for a in GENERIC_AGENT_CATALOG}
    assert {"research", "writer", "editor", "text_extract", "table_peek"}.issubset(ids)


def test_resolve_enabled_request_override():
    assert resolve_enabled_for_request(["editor"]) == ["editor"]
    assert resolve_enabled_for_request([]) == []
    assert resolve_enabled_for_request(None) == ["research", "writer"]


def test_build_agent_includes_agent_tools_for_research():
    from google.adk.tools.agent_tool import AgentTool
    from workflow_agent.agent import build_agent

    agent = build_agent("gemini-2.5-flash", ["research"])
    tool_types = [type(t) for t in agent.tools]
    assert AgentTool in tool_types
    assert len(agent.tools) >= 6  # 5 workflow + 1 research


def test_build_agent_no_delegates_when_empty():
    from google.adk.tools.agent_tool import AgentTool
    from workflow_agent.agent import build_agent

    agent = build_agent("gemini-2.5-flash", [])
    delegate_count = sum(1 for t in agent.tools if isinstance(t, AgentTool))
    assert delegate_count == 0


@pytest.mark.anyio
async def test_generic_agents_api(client: AsyncClient) -> None:
    r = await client.get("/api/workflow/generic-agents")
    assert r.status_code == 200
    agents = r.json()["agents"]
    assert len(agents) >= 8
    categories = {a["category"] for a in agents}
    assert "private_doc" in categories
    assert agents[0]["id"] in ("research", "writer", "editor")


@pytest.mark.anyio
async def test_workflow_settings_round_trip(client: AsyncClient) -> None:
    r = await client.put(
        "/api/workflow/settings",
        json={"enabled_generic_agents": ["writer", "editor"]},
    )
    assert r.status_code == 200
    assert r.json()["settings"]["enabled_generic_agents"] == ["writer", "editor"]

    r2 = await client.get("/api/workflow/settings")
    assert r2.status_code == 200
    assert set(r2.json()["settings"]["enabled_generic_agents"]) == {"writer", "editor"}

    r3 = await client.put("/api/workflow/settings", json={"advanced_mode": True})
    assert r3.status_code == 200
    assert r3.json()["settings"]["advanced_mode"] is True


@pytest.mark.anyio
async def test_create_workflow_stores_enabled_agents(client: AsyncClient) -> None:
    r = await client.post(
        "/api/requests",
        json={
            "title": "WF generic test",
            "description": "Test enabled specialists",
            "agent_type": "workflow",
            "priority": "normal",
            "enabled_generic_agents": ["research"],
        },
    )
    assert r.status_code == 202
    body = r.json()
    assert body["enabled_generic_agents"] == ["research"]

    r2 = await client.get(f"/api/requests/{body['id']}")
    assert r2.status_code == 200
    assert r2.json()["enabled_generic_agents"] == ["research"]
