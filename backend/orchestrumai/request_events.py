"""In-memory SSE event buffers for active requests."""

from __future__ import annotations

from typing import Any

_event_buffers: dict[str, list[dict[str, Any]]] = {}


def append_event(request_id: str, payload: dict[str, Any]) -> None:
    buf = _event_buffers.setdefault(request_id, [])
    buf.append(payload)
    if len(buf) > 200:
        del buf[:-200]


def get_events(request_id: str) -> list[dict[str, Any]]:
    return _event_buffers.get(request_id, [])


def init_events(request_id: str) -> None:
    _event_buffers[request_id] = []


def clear_events(request_id: str) -> None:
    _event_buffers.pop(request_id, None)
