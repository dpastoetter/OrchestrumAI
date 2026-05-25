"""Tests for workflow templates and schedules."""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ["ORCHESTRUMAI_STUB_RUN"] = "1"
os.environ["ORCHESTRUMAI_DATA_DIR"] = "/tmp/orchestrumai-test-templates"

from orchestrumai.app import create_app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    from orchestrumai.bundled_templates import ensure_bundled_templates_imported

    ensure_bundled_templates_imported()
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_bundled_templates_imported(client: AsyncClient) -> None:
    r = await client.get("/api/workflow-templates")
    assert r.status_code == 200
    names = {t["name"] for t in r.json()["templates"]}
    assert "Morning brief" in names
    assert "Weekly invoice review" in names


@pytest.mark.anyio
async def test_create_and_run_template(client: AsyncClient) -> None:
    create = await client.post(
        "/api/workflow-templates",
        json={
            "name": "Test template",
            "description_template": "Run for {{date}}",
            "agent_type": "workflow",
            "agent_topology": {
                "type": "simple",
                "nodes": [{"id": "n1", "kind": "catalog", "catalog_id": "research"}],
            },
        },
    )
    assert create.status_code == 201
    tpl_id = create.json()["id"]

    run = await client.post(
        f"/api/workflow-templates/{tpl_id}/run",
        json={"description_vars": {}},
    )
    assert run.status_code == 202
    assert "{{date}}" not in run.json()["description"]
    assert run.json()["workflow_template_id"] == tpl_id


@pytest.mark.anyio
async def test_schedule_crud(client: AsyncClient) -> None:
    tpl = await client.post(
        "/api/workflow-templates",
        json={
            "name": "Sched test",
            "description_template": "Daily task",
            "agent_type": "workflow",
            "agent_topology": {
                "type": "simple",
                "nodes": [{"id": "n1", "kind": "catalog", "catalog_id": "writer"}],
            },
        },
    )
    tpl_id = tpl.json()["id"]
    sched = await client.post(
        "/api/workflow-schedules",
        json={
            "template_id": tpl_id,
            "cron_expression": "0 8 * * *",
            "timezone": "UTC",
            "enabled": True,
        },
    )
    assert sched.status_code == 201
    assert sched.json()["next_run_at"] is not None

    listed = await client.get("/api/workflow-schedules")
    assert listed.status_code == 200
    assert any(s["id"] == sched.json()["id"] for s in listed.json()["schedules"])
