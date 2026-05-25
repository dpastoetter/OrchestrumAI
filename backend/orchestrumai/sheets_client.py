"""Google Sheets API client for appending extracted rows."""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from .config import DEFAULT_SPREADSHEET_ID, GOOGLE_APPLICATION_CREDENTIALS, SHEETS_WRITE_ENABLED

log = logging.getLogger(__name__)

_SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"


def parse_spreadsheet_id(sheet_url_or_id: str) -> str:
    """Extract spreadsheet ID from URL or raw ID."""
    value = (sheet_url_or_id or "").strip()
    if not value:
        return DEFAULT_SPREADSHEET_ID
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", value)
    if match:
        return match.group(1)
    return value


def _get_sheets_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_path = GOOGLE_APPLICATION_CREDENTIALS
    if not creds_path or not os.path.isfile(creds_path):
        raise ValueError(
            "GOOGLE_APPLICATION_CREDENTIALS must point to a service account JSON file"
        )
    credentials = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=[_SHEETS_SCOPE],
    )
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def append_rows(
    spreadsheet_id: str,
    rows: list[dict[str, Any]],
    columns: list[str],
    *,
    sheet_name: str = "Sheet1",
    stub: bool = False,
) -> dict[str, Any]:
    """Append rows to a Google Sheet. Returns {spreadsheet_id, rows_written, sheet_url}."""
    if not rows:
        raise ValueError("No rows to append")

    sid = parse_spreadsheet_id(spreadsheet_id)
    if not sid:
        raise ValueError("No spreadsheet ID configured (DEFAULT_SPREADSHEET_ID or sheet_url)")

    values = [[str(row.get(col, "")) for col in columns] for row in rows]

    if stub or not SHEETS_WRITE_ENABLED:
        log.info("Stub/mock Sheets append: %s rows to %s", len(values), sid)
        return {
            "spreadsheet_id": sid,
            "rows_written": len(values),
            "sheet_url": f"https://docs.google.com/spreadsheets/d/{sid} (stub — not written)",
            "stub": True,
        }

    service = _get_sheets_service()
    range_name = f"{sheet_name}!A1"
    body = {"values": values}
    result = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=sid,
            range=range_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        )
        .execute()
    )
    updated = result.get("updates", {}).get("updatedRows", len(values))
    return {
        "spreadsheet_id": sid,
        "rows_written": updated,
        "sheet_url": f"https://docs.google.com/spreadsheets/d/{sid}",
        "stub": False,
    }
