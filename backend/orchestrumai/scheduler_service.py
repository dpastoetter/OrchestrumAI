"""APScheduler-driven workflow template runs."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import BackgroundTasks

from .cron_utils import compute_next_run
from .request_format import record_to_summary
from .request_service import create_request_from_template
from .request_store import RequestStore
from .runner_bridge import get_runner_bridge
from .template_store import TemplateStore, WorkflowScheduleRecord, WorkflowTemplateRecord, parse_json_field

log = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_service: SchedulerService | None = None


class SchedulerService:
    def __init__(self) -> None:
        self._store = TemplateStore()
        self._requests = RequestStore()
        self._bridge = get_runner_bridge()
        self._lock = asyncio.Lock()
        self._pending_background: BackgroundTasks | None = None

    def set_background_tasks(self, background: BackgroundTasks) -> None:
        self._pending_background = background

    async def tick(self) -> None:
        async with self._lock:
            now = datetime.now(timezone.utc)
            for sched in self._store.list_enabled_schedules():
                if sched.next_run_at is None:
                    continue
                if sched.next_run_at > now:
                    continue
                tpl = self._store.get_template(sched.template_id)
                if tpl is None:
                    continue
                bg = self._pending_background or BackgroundTasks()
                await self.run_schedule(sched, tpl, background=bg, force=False)

    async def run_schedule(
        self,
        sched: WorkflowScheduleRecord,
        tpl: WorkflowTemplateRecord,
        *,
        background: BackgroundTasks,
        force: bool,
    ):
        if not force and sched.last_request_id:
            prev = self._requests.get(sched.last_request_id)
            if prev and prev.status in ("active", "awaiting_approval"):
                log.info(
                    "Skip schedule %s: prior request %s still %s",
                    sched.id,
                    prev.id,
                    prev.status,
                )
                self._bump_next_run(sched)
                return None

        vars = parse_json_field(sched.description_vars, {})
        if not isinstance(vars, dict):
            vars = {}

        try:
            summary = await create_request_from_template(
                background=background,
                bridge=self._bridge,
                template=tpl,
                user_id=sched.user_id,
                description_vars=vars,
                workflow_schedule_id=sched.id,
                run_source="scheduled",
            )
        except Exception as exc:
            log.exception("Scheduled run failed for %s: %s", sched.id, exc)
            self._bump_next_run(sched)
            return None

        self._store.update_schedule(
            sched.id,
            last_run_at=datetime.now(timezone.utc),
            last_request_id=summary.id,
        )
        self._bump_next_run(sched)
        log.info("Scheduled workflow %s -> request %s", sched.id, summary.id)
        return summary

    def _bump_next_run(self, sched: WorkflowScheduleRecord) -> None:
        try:
            nxt = compute_next_run(sched.cron_expression, sched.timezone)
            self._store.update_schedule(sched.id, next_run_at=nxt)
        except Exception as exc:
            log.warning("Could not compute next run for %s: %s", sched.id, exc)

    def refresh(self) -> None:
        pass


def get_scheduler_service() -> SchedulerService:
    global _service
    if _service is None:
        _service = SchedulerService()
    return _service


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _job_tick,
        "interval",
        seconds=60,
        id="workflow_schedule_tick",
        replace_existing=True,
    )
    _scheduler.start()
    log.info("Workflow schedule scheduler started")
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("Workflow schedule scheduler stopped")


async def _job_tick() -> None:
    await get_scheduler_service().tick()
