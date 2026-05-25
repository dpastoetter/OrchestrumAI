"""Tests for document-to-sheets agent and parsers."""

from __future__ import annotations

import asyncio
import csv
import json
import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

os.environ["OPENMINIAGENTS_STUB_RUN"] = "1"
os.environ["OPENMINIAGENTS_DATA_DIR"] = "/tmp/openminiagents-doc-test"
os.environ["SHEETS_WRITE_ENABLED"] = "0"

from openminiagents.app import create_app
from openminiagents.document_parser import extract_table
from openminiagents.sheets_client import append_rows, parse_spreadsheet_id


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def test_parse_spreadsheet_id_from_url():
    url = "https://docs.google.com/spreadsheets/d/abc123XYZ/edit#gid=0"
    assert parse_spreadsheet_id(url) == "abc123XYZ"


def test_extract_table_stub():
    table = extract_table("/nonexistent/path.csv", stub=True)
    assert len(table["columns"]) == 3
    assert len(table["rows"]) == 3


def test_extract_table_csv(tmp_path: Path):
    path = tmp_path / "data.csv"
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Name", "Value"])
        writer.writeheader()
        writer.writerow({"Name": "A", "Value": "1"})
        writer.writerow({"Name": "B", "Value": "2"})
    table = extract_table(str(path), stub=False)
    assert table["columns"] == ["Name", "Value"]
    assert len(table["rows"]) == 2
    assert table["rows"][0]["Name"] == "A"


def test_append_rows_stub():
    result = append_rows(
        "test-sheet-id",
        [{"A": "1", "B": "2"}],
        ["A", "B"],
        stub=True,
    )
    assert result["rows_written"] == 1
    assert result["stub"] is True
    assert "test-sheet-id" in result["sheet_url"]


@pytest.mark.anyio
async def test_doc_to_sheets_upload_flow(client: AsyncClient, tmp_path: Path) -> None:
    csv_path = tmp_path / "expenses.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Date", "Amount"])
        writer.writeheader()
        writer.writerow({"Date": "2026-01-01", "Amount": "10"})

    with csv_path.open("rb") as f:
        create = await client.post(
            "/api/requests/upload",
            data={
                "title": "Expense import",
                "description": "Import expenses to sheet",
                "priority": "normal",
                "agent_type": "doc_to_sheets",
                "sheet_url": "",
            },
            files={"file": ("expenses.csv", f, "text/csv")},
        )
    assert create.status_code == 202
    req_id = create.json()["id"]
    assert create.json()["agent_type"] == "doc_to_sheets"

    detail = None
    for _ in range(40):
        await asyncio.sleep(0.25)
        detail = await client.get(f"/api/requests/{req_id}")
        assert detail.status_code == 200
        body = detail.json()
        if body["current_step"] == "AWAITING_APPROVAL":
            break
    assert detail is not None
    body = detail.json()
    assert body["current_step"] == "AWAITING_APPROVAL"
    assert len(body["preview_rows"]) >= 1
    assert "Date" in body["columns"] or len(body["columns"]) > 0

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
    assert "rows" in detail.json()["result_summary"].lower() or detail.json()["rows_written"]


@pytest.mark.anyio
async def test_list_agents(client: AsyncClient) -> None:
    r = await client.get("/api/agents")
    assert r.status_code == 200
    ids = {a["id"] for a in r.json()}
    assert "doc_to_sheets" in ids
    assert "workflow" in ids
