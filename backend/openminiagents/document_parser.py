"""Extract structured rows from uploaded documents."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


def _parse_csv_xlsx(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    import pandas as pd

    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path, engine="openpyxl")
    df = df.fillna("")
    columns = [str(c) for c in df.columns.tolist()]
    rows: list[dict[str, Any]] = []
    for _, row in df.head(500).iterrows():
        rows.append({columns[i]: str(row.iloc[i]) for i in range(len(columns))})
    return columns, rows


def _parse_with_gemini(path: Path, mime_hint: str, description: str) -> tuple[list[str], list[dict[str, Any]]]:
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is required for PDF/image extraction")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    suffix = path.suffix.lower()
    prompt = (
        "Extract all tabular or list-like data from this document as JSON with exactly this shape:\n"
        '{"columns": ["col1", "col2"], "rows": [{"col1": "a", "col2": "b"}]}\n'
        "Use consistent column names. Include every data row you can find (up to 100 rows).\n"
        f"User context: {description[:2000]}"
    )

    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        with path.open("rb") as f:
            image_bytes = f.read()
        mime = mime_hint if mime_hint.startswith("image/") else f"image/{suffix.lstrip('.')}"
        response = client.models.generate_content(
            model=os.environ.get("ADK_DEFAULT_MODEL", "gemini-2.5-flash"),
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part(text=prompt),
                        types.Part(inline_data=types.Blob(mime_type=mime, data=image_bytes)),
                    ],
                )
            ],
        )
    else:
        # PDF: upload file
        uploaded = client.files.upload(file=str(path))
        response = client.models.generate_content(
            model=os.environ.get("ADK_DEFAULT_MODEL", "gemini-2.5-flash"),
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part(text=prompt),
                        types.Part(file_data=types.FileData(file_uri=uploaded.uri)),
                    ],
                )
            ],
        )

    text = response.text or ""
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("Model did not return JSON table data")
    data = json.loads(match.group())
    columns = [str(c) for c in data.get("columns", [])]
    rows = data.get("rows", [])
    if not columns or not rows:
        raise ValueError("Extraction returned empty columns or rows")
    normalized: list[dict[str, Any]] = []
    for row in rows[:500]:
        if isinstance(row, dict):
            normalized.append({k: str(v) for k, v in row.items()})
    return columns, normalized


def extract_table(
    file_path: str,
    *,
    mime_type: str = "",
    description: str = "",
    stub: bool = False,
    provider_id: str | None = None,
    model_id: str | None = None,
) -> dict[str, Any]:
    """Return {columns, rows, source, confidence_notes}."""
    if stub:
        return {
            "columns": ["Date", "Description", "Amount"],
            "rows": [
                {"Date": "2026-01-15", "Description": "Office supplies", "Amount": "42.50"},
                {"Date": "2026-01-18", "Description": "Software license", "Amount": "199.00"},
                {"Date": "2026-01-22", "Description": "Travel", "Amount": "320.00"},
            ],
            "source": "stub",
            "confidence_notes": "Stub extraction for offline testing.",
        }

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(file_path)

    suffix = path.suffix.lower()
    if suffix in {".csv", ".xlsx", ".xls"}:
        columns, rows = _parse_csv_xlsx(path)
        return {
            "columns": columns,
            "rows": rows,
            "source": "pandas",
            "confidence_notes": "Parsed directly from spreadsheet file.",
        }

    columns, rows = _parse_with_llm(
        path, mime_type, description, provider_id=provider_id, model_id=model_id
    )
    return {
        "columns": columns,
        "rows": rows,
        "source": "llm",
        "confidence_notes": "Extracted via configured LLM provider.",
    }


def _parse_with_llm(
    path: Path,
    mime_hint: str,
    description: str,
    *,
    provider_id: str | None,
    model_id: str | None,
) -> tuple[list[str], list[dict[str, Any]]]:
    from .llm_providers import build_adk_model, get_provider

    resolved = build_adk_model(provider_id or "", model_id)
    provider = get_provider(resolved.provider_id)
    if provider and provider.native_gemini:
        return _parse_with_gemini(path, mime_hint, description)
    if provider and provider.id == "chatgpt_oauth":
        return _parse_with_codex_text(path, description, resolved)
    return _parse_with_litellm_text(path, description, resolved)


def _parse_with_codex_text(
    path: Path,
    description: str,
    resolved: Any,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Text extraction via ChatGPT Codex OAuth /responses API."""
    import asyncio

    from .codex_client import codex_completion_text

    text = path.read_text(encoding="utf-8", errors="replace")[:120_000]
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages[:30])
        except Exception:
            text = "(PDF text extraction failed; install pypdf)"

    prompt = (
        "Extract tabular data as JSON: "
        '{"columns": ["col1"], "rows": [{"col1": "val"}]}\n'
        f"Context: {description[:1500]}\n\nDocument:\n{text[:80000]}"
    )
    model = resolved.model_id
    raw = asyncio.run(codex_completion_text(model, prompt, temperature=0.1))
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise ValueError("Model did not return JSON table data")
    data = json.loads(match.group())
    columns = [str(c) for c in data.get("columns", [])]
    rows = [
        {k: str(v) for k, v in row.items()}
        for row in data.get("rows", [])[:500]
        if isinstance(row, dict)
    ]
    if not columns or not rows:
        raise ValueError("Extraction returned empty columns or rows")
    return columns, rows


def _parse_with_litellm_text(
    path: Path,
    description: str,
    resolved: Any,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Text-only extraction for non-Gemini providers (CSV-like prompt)."""
    from .llm_providers import _ensure_litellm

    _ensure_litellm()
    import litellm

    text = path.read_text(encoding="utf-8", errors="replace")[:120_000]
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages[:30])
        except Exception:
            text = "(PDF text extraction failed; install pypdf or use Gemini provider)"

    prompt = (
        "Extract tabular data as JSON: "
        '{"columns": ["col1"], "rows": [{"col1": "val"}]}\n'
        f"Context: {description[:1500]}\n\nDocument:\n{text[:80000]}"
    )
    model = resolved.adk_model.model if hasattr(resolved.adk_model, "model") else str(resolved.adk_model)
    response = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    raw = response.choices[0].message.content or ""
    import re

    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise ValueError("Model did not return JSON table data")
    data = json.loads(match.group())
    columns = [str(c) for c in data.get("columns", [])]
    rows = [{k: str(v) for k, v in row.items()} for row in data.get("rows", [])[:500] if isinstance(row, dict)]
    if not columns or not rows:
        raise ValueError("Extraction returned empty columns or rows")
    return columns, rows


def default_column_mapping(columns: list[str]) -> dict[str, str]:
    """Identity mapping from extracted column to sheet column."""
    return {c: c for c in columns}
