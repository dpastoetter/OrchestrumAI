"""Render {{date}}, {{week}}, and custom vars in workflow description templates."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

_PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def _builtin_vars(now: datetime | None = None) -> dict[str, str]:
    dt = now or datetime.now(timezone.utc)
    return {
        "date": dt.strftime("%Y-%m-%d"),
        "week": dt.strftime("%Y-W%W"),
        "datetime": dt.isoformat(timespec="seconds"),
        "year": str(dt.year),
        "month": dt.strftime("%B %Y"),
    }


def render_description_template(
    template: str,
    *,
    vars: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> str:
    merged = {**_builtin_vars(now), **(vars or {})}

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in merged:
            return str(merged[key])
        return match.group(0)

    return _PLACEHOLDER.sub(repl, template)
