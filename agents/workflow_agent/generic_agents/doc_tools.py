"""Local document tools for private-realm workflow specialists."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from google.adk.tools import ToolContext
from google.adk.tools.function_tool import FunctionTool

_BACKEND = Path(__file__).resolve().parent.parent.parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from orchestrumai.config import STUB_RUN, UPLOADS_DIR  # noqa: E402


def _resolve_upload_path(tool_context: ToolContext, file_path: str = "") -> Path | None:
    path_str = (file_path or "").strip() or str(tool_context.state.get("file_path", ""))
    if not path_str:
        return None
    path = Path(path_str).resolve()
    uploads_root = UPLOADS_DIR.resolve()
    if uploads_root not in path.parents and path != uploads_root:
        return None
    if not path.is_file():
        return None
    return path


def read_local_excerpt(
    tool_context: ToolContext,
    file_path: str = "",
    page_start: int = 1,
    page_end: int = 0,
    max_chars: int = 50_000,
) -> dict[str, str]:
    """Read text from the uploaded file in session state (local data/uploads only)."""
    path = _resolve_upload_path(tool_context, file_path)
    if path is None:
        return {
            "error": "No file_path in session. Upload a file on Submit or paste text in the request.",
            "content": "",
        }

    suffix = path.suffix.lower()
    max_chars = max(1000, min(max_chars, 100_000))
    page_start = max(1, page_start)
    page_end = page_end if page_end >= page_start else 0

    try:
        if suffix in {".txt", ".md"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            pages = 1
        elif suffix == ".pdf":
            try:
                from pypdf import PdfReader
            except ImportError:
                return {
                    "error": "pypdf not installed. pip install 'orchestrumai[llm]' or pypdf.",
                    "content": "",
                }
            reader = PdfReader(str(path))
            pages = len(reader.pages)
            end = page_end or pages
            end = min(end, pages)
            parts: list[str] = []
            for i in range(page_start - 1, end):
                parts.append(reader.pages[i].extract_text() or "")
            text = "\n".join(parts)
        else:
            return {
                "error": f"read_local_excerpt does not support {suffix}. Use table_peek for spreadsheets.",
                "content": "",
            }
    except Exception as exc:
        return {"error": str(exc), "content": ""}

    excerpt = text[:max_chars]
    return {
        "file_path": str(path),
        "page_count": str(pages),
        "chars": str(len(text)),
        "truncated": str(len(text) > max_chars).lower(),
        "content": excerpt,
    }


def peek_table(
    tool_context: ToolContext,
    file_path: str = "",
    description: str = "",
) -> dict[str, object]:
    """Extract tabular preview from CSV/XLSX/PDF (no Google Sheets write)."""
    path = _resolve_upload_path(tool_context, file_path)
    if path is None:
        return {"error": "No file_path in session. Upload a spreadsheet or document first."}

    from orchestrumai.document_parser import extract_table

    desc = (description or "").strip() or str(tool_context.state.get("request_description", ""))
    mime = str(tool_context.state.get("file_mime_type", ""))
    provider_id = str(tool_context.state.get("llm_provider_id", "")) or None
    model_id = str(tool_context.state.get("llm_model_id", "")) or None

    table = extract_table(
        str(path),
        mime_type=mime,
        description=desc,
        stub=STUB_RUN,
        provider_id=provider_id,
        model_id=model_id,
    )
    columns = table.get("columns", [])
    rows = table.get("rows", [])[:20]
    preview_md = _rows_to_markdown(columns, rows)
    return {
        "columns": columns,
        "row_count": len(table.get("rows", [])),
        "preview_rows": rows,
        "markdown_preview": preview_md,
        "source": table.get("source", ""),
        "confidence_notes": table.get("confidence_notes", ""),
    }


def ocr_check(tool_context: ToolContext, file_path: str = "") -> dict[str, str]:
    """Heuristic: PDF with little extractable text may be scanned."""
    path = _resolve_upload_path(tool_context, file_path)
    if path is None:
        return {"error": "No file_path in session", "likely_scanned": "unknown"}

    if path.suffix.lower() != ".pdf":
        return {
            "file_path": str(path),
            "likely_scanned": "false",
            "note": "OCR check applies to PDF only.",
        }

    try:
        from pypdf import PdfReader
    except ImportError:
        return {"error": "pypdf not installed", "likely_scanned": "unknown"}

    try:
        reader = PdfReader(str(path))
        sample = ""
        for page in reader.pages[:3]:
            sample += page.extract_text() or ""
        chars = len(sample.strip())
        likely = chars < 80
        return {
            "file_path": str(path),
            "sample_chars": str(chars),
            "likely_scanned": str(likely).lower(),
            "note": (
                "Little text extracted; may need OCR or a clearer scan."
                if likely
                else "Text layer present."
            ),
        }
    except Exception as exc:
        return {"error": str(exc), "likely_scanned": "unknown"}


def _rows_to_markdown(columns: list[str], rows: list[dict]) -> str:
    if not columns:
        return "(no columns)"
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body_lines = []
    for row in rows:
        body_lines.append("| " + " | ".join(str(row.get(c, "")) for c in columns) + " |")
    return "\n".join([header, sep, *body_lines])


def regex_redact_preview(text: str) -> tuple[str, list[str]]:
    """Deterministic PII-ish masking for manifest (not full redactor)."""
    manifest: list[str] = []
    out = text
    patterns = [
        (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[EMAIL]"),
        (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE]"),
    ]
    for pat, repl in patterns:
        if re.search(pat, out):
            manifest.append(repl.strip("[]"))
            out = re.sub(pat, repl, out)
    return out, manifest


def grep_doc(
    tool_context: ToolContext,
    query: str,
    file_path: str = "",
    max_hits: int = 20,
) -> dict[str, object]:
    """Search for a keyword/phrase in the uploaded local document text."""
    q = (query or "").strip()
    if not q:
        return {"error": "query is required", "hits": []}
    excerpt = read_local_excerpt(tool_context, file_path=file_path, max_chars=80_000)
    if excerpt.get("error"):
        return {"error": excerpt["error"], "hits": []}
    content = str(excerpt.get("content", ""))
    hits: list[dict[str, str]] = []
    lower = content.lower()
    needle = q.lower()
    start = 0
    while len(hits) < max(1, min(max_hits, 50)):
        idx = lower.find(needle, start)
        if idx < 0:
            break
        line_start = content.rfind("\n", 0, idx) + 1
        line_end = content.find("\n", idx)
        if line_end < 0:
            line_end = len(content)
        snippet = content[line_start:line_end].strip()
        hits.append({"line": snippet[:500], "offset": str(idx)})
        start = idx + len(needle)
    return {
        "query": q,
        "hit_count": len(hits),
        "hits": hits,
        "truncated": excerpt.get("truncated", "false"),
    }


def doc_profile(
    tool_context: ToolContext,
    file_path: str = "",
) -> dict[str, object]:
    """Summarize uploaded file: type, size, text sample, table hint, OCR risk."""
    path = _resolve_upload_path(tool_context, file_path)
    if path is None:
        return {"error": "No file_path in session. Upload a file first."}

    profile: dict[str, object] = {
        "file_path": str(path),
        "file_name": path.name,
        "suffix": path.suffix.lower(),
        "size_bytes": path.stat().st_size,
    }

    ocr = ocr_check(tool_context, file_path=file_path)
    profile["ocr_check"] = ocr

    suffix = path.suffix.lower()
    if suffix in {".csv", ".xlsx", ".xls"}:
        peek = peek_table(tool_context, file_path=file_path)
        profile["table_preview"] = {
            "columns": peek.get("columns", []),
            "row_count": peek.get("row_count", 0),
            "source": peek.get("source", ""),
        }
    else:
        excerpt = read_local_excerpt(
            tool_context, file_path=file_path, page_start=1, page_end=3, max_chars=8000
        )
        profile["text_sample"] = (excerpt.get("content") or "")[:2000]
        profile["page_count"] = excerpt.get("page_count", "")
        if excerpt.get("error"):
            profile["read_error"] = excerpt["error"]

    return profile


grep_doc_tool = FunctionTool(grep_doc)
doc_profile_tool = FunctionTool(doc_profile)
read_local_excerpt_tool = FunctionTool(read_local_excerpt)
peek_table_tool = FunctionTool(peek_table)
ocr_check_tool = FunctionTool(ocr_check)
