"""Local storage for uploaded documents."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile

from .config import UPLOADS_DIR, ensure_data_dir

ALLOWED_EXTENSIONS = frozenset({".pdf", ".csv", ".xlsx", ".xls", ".png", ".jpg", ".jpeg", ".webp"})
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def save_upload(file: UploadFile) -> tuple[str, str, str]:
    """Save upload; returns (stored_path, original_filename, content_type)."""
    ensure_data_dir()
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    original = file.filename or "upload"
    suffix = Path(original).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{suffix}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    data = file.file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"File exceeds maximum size of {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")

    stored_name = f"{uuid.uuid4()}{suffix}"
    path = UPLOADS_DIR / stored_name
    path.write_bytes(data)

    content_type = file.content_type or "application/octet-stream"
    return str(path.resolve()), original, content_type
