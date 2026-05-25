"""Tests for private-realm workflow catalog agents and doc tools."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from google.adk.tools.agent_tool import AgentTool

os.environ["ORCHESTRUMAI_STUB_RUN"] = "1"
os.environ["ORCHESTRUMAI_DATA_DIR"] = "/tmp/orchestrumai-private-test"

from httpx import ASGITransport, AsyncClient

from orchestrumai.app import create_app
from workflow_agent.generic_agents.catalog import GENERIC_AGENT_CATALOG, tool_name_for
from workflow_agent.generic_agents.doc_tools import doc_profile, grep_doc, peek_table, read_local_excerpt
from workflow_agent.topology import AgentTopology
from workflow_agent.topology_builder import build_agent_from_topology


FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_catalog_includes_private_agents():
    ids = {a.id for a in GENERIC_AGENT_CATALOG}
    assert "text_extract" in ids
    assert "table_peek" in ids
    assert "pii_redactor" in ids
    assert "invoice_parser" in ids
    assert "contract_clauses" in ids
    assert "grep_doc" in ids
    assert "doc_profile" in ids


def test_grep_doc_finds_keyword(tmp_path, monkeypatch):
    monkeypatch.setenv("ORCHESTRUMAI_DATA_DIR", str(tmp_path))
    from orchestrumai.config import UPLOADS_DIR

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    f = UPLOADS_DIR / "note.txt"
    f.write_text("hello invoice world\nsecond line", encoding="utf-8")
    ctx = MagicMock()
    ctx.state = {"file_path": str(f.resolve())}
    out = grep_doc(ctx, query="invoice")
    assert out["hit_count"] >= 1


def test_doc_profile_txt(tmp_path, monkeypatch):
    monkeypatch.setenv("ORCHESTRUMAI_DATA_DIR", str(tmp_path))
    from orchestrumai.config import UPLOADS_DIR

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    f = UPLOADS_DIR / "doc.txt"
    f.write_text("short document body", encoding="utf-8")
    ctx = MagicMock()
    ctx.state = {"file_path": str(f.resolve())}
    out = doc_profile(ctx)
    assert out.get("suffix") == ".txt"
    assert "text_sample" in out


def test_tool_names_for_private_agents():
    assert tool_name_for("text_extract") == "text_extract_agent"
    assert tool_name_for("invoice_parser") == "invoice_parser_agent"


def test_build_orchestrator_with_private_delegate():
    topo = AgentTopology.model_validate(
        {
            "type": "orchestrator",
            "nodes": [
                {"id": "n1", "kind": "catalog", "catalog_id": "text_extract"},
                {"id": "n2", "kind": "catalog", "catalog_id": "invoice_parser"},
            ],
            "edges": [],
        }
    )
    agent = build_agent_from_topology("gemini-2.5-flash", topo)
    assert sum(1 for t in agent.tools if isinstance(t, AgentTool)) == 2


def test_read_local_excerpt_txt(tmp_path, monkeypatch):
    from orchestrumai.config import UPLOADS_DIR

    monkeypatch.setattr("workflow_agent.generic_agents.doc_tools.UPLOADS_DIR", tmp_path)
    sample = tmp_path / "note.txt"
    sample.write_text("Hello private realm", encoding="utf-8")

    ctx = MagicMock()
    ctx.state = {"file_path": str(sample)}
    result = read_local_excerpt(ctx)
    assert "Hello private realm" in result["content"]
    assert result.get("error", "") == ""


def test_peek_table_csv(tmp_path, monkeypatch):
    monkeypatch.setattr("workflow_agent.generic_agents.doc_tools.UPLOADS_DIR", tmp_path)
    monkeypatch.setattr("workflow_agent.generic_agents.doc_tools.STUB_RUN", False)
    csv_path = tmp_path / "data.csv"
    csv_path.write_text((FIXTURES / "sample.csv").read_text(), encoding="utf-8")

    ctx = MagicMock()
    ctx.state = {"file_path": str(csv_path), "request_description": "inventory"}
    result = peek_table(ctx)
    assert result.get("columns") == ["item", "qty", "price"]
    assert result.get("row_count", 0) >= 2


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_generic_agents_api_lists_categories(client: AsyncClient):
    r = await client.get("/api/workflow/generic-agents")
    assert r.status_code == 200
    agents = r.json()["agents"]
    private = [a for a in agents if a.get("category") == "private_doc"]
    assert len(private) >= 5


@pytest.mark.anyio
async def test_workflow_upload_stores_file_path(client: AsyncClient, tmp_path, monkeypatch):
    from orchestrumai import file_storage
    from orchestrumai.config import UPLOADS_DIR

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr("orchestrumai.config.UPLOADS_DIR", upload_dir)
    monkeypatch.setattr("orchestrumai.file_storage.UPLOADS_DIR", upload_dir)

    csv_bytes = (FIXTURES / "sample.csv").read_bytes()
    topology = json.dumps(
        {
            "type": "orchestrator",
            "nodes": [{"id": "n1", "kind": "catalog", "catalog_id": "table_peek"}],
            "edges": [],
        }
    )
    r = await client.post(
        "/api/requests/upload",
        data={
            "title": "Private upload",
            "description": "Parse local CSV",
            "priority": "normal",
            "agent_type": "workflow",
            "agent_topology_json": topology,
        },
        files={"file": ("sample.csv", csv_bytes, "text/csv")},
    )
    assert r.status_code == 202, r.text
    detail = await client.get(f"/api/requests/{r.json()['id']}")
    assert detail.status_code == 200
