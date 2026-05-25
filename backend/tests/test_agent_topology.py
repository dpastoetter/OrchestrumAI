"""Tests for per-request agent topology builder."""

from __future__ import annotations

import json

import pytest
from google.adk.tools.agent_tool import AgentTool
from httpx import ASGITransport, AsyncClient

from openminiagents.app import create_app
from workflow_agent.topology import AgentTopology, TopologyNode
from workflow_agent.topology_builder import build_agent_from_topology


def _orchestrator_topology() -> dict:
    return {
        "type": "orchestrator",
        "nodes": [
            {"id": "n1", "kind": "catalog", "catalog_id": "research"},
            {"id": "n2", "kind": "catalog", "catalog_id": "writer"},
        ],
        "edges": [],
    }


def _sequential_topology() -> dict:
    return {
        "type": "sequential",
        "nodes": [
            {"id": "n1", "kind": "catalog", "catalog_id": "research"},
            {"id": "n2", "kind": "catalog", "catalog_id": "writer"},
        ],
        "edges": [{"from": "n1", "to": "n2"}],
    }


def _simple_topology() -> dict:
    return {
        "type": "simple",
        "nodes": [{"id": "n1", "kind": "catalog", "catalog_id": "writer"}],
        "edges": [],
    }


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def test_topology_validation_simple_requires_one_node():
    with pytest.raises(ValueError, match="exactly one"):
        AgentTopology.model_validate(
            {"type": "simple", "nodes": [], "edges": []},
        )


def test_topology_validation_sequential_requires_two():
    with pytest.raises(ValueError, match="at least two"):
        AgentTopology.model_validate(
            {"type": "sequential", "nodes": [{"id": "n1", "kind": "catalog", "catalog_id": "research"}], "edges": []},
        )


def test_build_orchestrator_has_delegate_tools():
    topo = AgentTopology.model_validate(_orchestrator_topology())
    agent = build_agent_from_topology("gemini-2.5-flash", topo)
    delegate_count = sum(1 for t in agent.tools if isinstance(t, AgentTool))
    assert delegate_count == 2


def test_build_sequential_has_pipeline_tool():
    topo = AgentTopology.model_validate(_sequential_topology())
    agent = build_agent_from_topology("gemini-2.5-flash", topo)
    delegate_count = sum(1 for t in agent.tools if isinstance(t, AgentTool))
    assert delegate_count == 1


def test_build_simple_no_delegate_tools():
    topo = AgentTopology.model_validate(_simple_topology())
    agent = build_agent_from_topology("gemini-2.5-flash", topo)
    delegate_count = sum(1 for t in agent.tools if isinstance(t, AgentTool))
    assert delegate_count == 0


def test_custom_node_requires_instruction():
    with pytest.raises(ValueError):
        TopologyNode.model_validate(
            {"id": "c1", "kind": "custom", "name": "My agent", "instruction": ""},
        )


@pytest.mark.anyio
async def test_create_request_stores_topology(client: AsyncClient):
    r = await client.post(
        "/api/requests",
        json={
            "title": "Topology test",
            "description": "Verify agent topology persistence",
            "agent_type": "workflow",
            "agent_topology": _orchestrator_topology(),
        },
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["agent_topology_type"] == "orchestrator"
    assert "Research" in body["agent_topology_labels"]
    assert "Writer" in body["agent_topology_labels"]

    r2 = await client.get(f"/api/requests/{body['id']}")
    assert r2.status_code == 200
    assert r2.json()["agent_topology_type"] == "orchestrator"


@pytest.mark.anyio
async def test_runner_keys_differ_by_topology():
    from openminiagents.runner_bridge import RunnerBridge

    bridge = RunnerBridge()
    k1 = bridge._runner_key("workflow", None, None, agent_topology=_orchestrator_topology())
    k2 = bridge._runner_key("workflow", None, None, agent_topology=_sequential_topology())
    assert k1 != k2
