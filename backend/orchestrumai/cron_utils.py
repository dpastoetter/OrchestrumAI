"""Cron expression helpers using croniter."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from croniter import croniter


def compute_next_run(cron_expression: str, tz_name: str, base: datetime | None = None) -> datetime:
    """Return next fire time in UTC."""
    tz = ZoneInfo(tz_name) if tz_name else ZoneInfo("UTC")
    if base is None:
        base_local = datetime.now(tz)
    else:
        base_local = base.astimezone(tz)
    itr = croniter(cron_expression, base_local)
    next_local = itr.get_next(datetime)
    if next_local.tzinfo is None:
        next_local = next_local.replace(tzinfo=tz)
    return next_local.astimezone(timezone.utc)


def validate_cron(cron_expression: str) -> None:
    try:
        croniter(cron_expression)
    except (ValueError, KeyError) as exc:
        raise ValueError(f"Invalid cron expression: {exc}") from exc
