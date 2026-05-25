"""API smoke tests (stub mode — no Gemini calls)."""

from __future__ import annotations

import asyncio
import os
import time

import pytest
from httpx import ASGITransport, AsyncClient

os.environ["ORCHESTRUMAI_STUB_RUN"] = "1"
os.environ["ORCHESTRUMAI_DATA_DIR"] = "/tmp/orchestrumai-test-data"

from orchestrumai.app import create_app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_health(client: AsyncClient) -> None:
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.anyio
async def test_create_and_approve_workflow(client: AsyncClient) -> None:
    create = await client.post(
        "/api/requests",
        json={
            "title": "Test request",
            "description": "Summarize the benefits of unit tests.",
            "priority": "normal",
            "agent_type": "workflow",
        },
    )
    assert create.status_code == 202
    req_id = create.json()["id"]

    detail = None
    for _ in range(40):
        await asyncio.sleep(0.25)
        detail = await client.get(f"/api/requests/{req_id}")
        assert detail.status_code == 200
        if detail.json()["current_step"] == "AWAITING_APPROVAL":
            break
    assert detail is not None
    assert detail.json()["current_step"] == "AWAITING_APPROVAL"

    resume = await client.post(
        f"/api/requests/{req_id}/resume",
        json={"decision": "approved", "comment": "Looks good"},
    )
    assert resume.status_code == 200

    for _ in range(40):
        await asyncio.sleep(0.25)
        detail = await client.get(f"/api/requests/{req_id}")
        if detail.json()["current_step"] == "COMPLETED":
            break
    assert detail.json()["current_step"] == "COMPLETED"
    assert detail.json()["status"] == "done"


@pytest.mark.anyio
async def test_list_requests(client: AsyncClient) -> None:
    r = await client.get("/api/requests")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.anyio
async def test_delete_request(client: AsyncClient) -> None:
    create = await client.post(
        "/api/requests",
        json={
            "title": "To delete",
            "description": "Remove me",
            "priority": "normal",
            "agent_type": "workflow",
        },
    )
    assert create.status_code == 202
    req_id = create.json()["id"]

    deleted = await client.delete(f"/api/requests/{req_id}")
    assert deleted.status_code == 204

    gone = await client.get(f"/api/requests/{req_id}")
    assert gone.status_code == 404

    listed = await client.get("/api/requests")
    assert all(r["id"] != req_id for r in listed.json())
