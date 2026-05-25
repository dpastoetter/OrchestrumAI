"""SQLite persistence for workflow templates and schedules."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .config import REQUESTS_DB_PATH, ensure_data_dir


class Base(DeclarativeBase):
    pass


class WorkflowTemplateRecord(Base):
    __tablename__ = "workflow_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description_template: Mapped[str] = mapped_column(Text)
    agent_type: Mapped[str] = mapped_column(String(32), default="workflow")
    agent_topology: Mapped[str] = mapped_column(Text, default="")
    default_priority: Mapped[str] = mapped_column(String(16), default="normal")
    provider_id: Mapped[str] = mapped_column(String(32), default="")
    model_id: Mapped[str] = mapped_column(String(64), default="")
    require_plan_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    icon: Mapped[str] = mapped_column(String(16), default="")
    category: Mapped[str] = mapped_column(String(32), default="general")
    bundled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WorkflowScheduleRecord(Base):
    __tablename__ = "workflow_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    template_id: Mapped[str] = mapped_column(String(36), index=True)
    cron_expression: Mapped[str] = mapped_column(String(128))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    description_vars: Mapped[str] = mapped_column(Text, default="{}")
    on_approval: Mapped[str] = mapped_column(String(32), default="pause")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_request_id: Mapped[str] = mapped_column(String(36), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


_REQUEST_EXTRA_COLUMNS = {
    "workflow_template_id": "VARCHAR(36) DEFAULT ''",
    "workflow_schedule_id": "VARCHAR(36) DEFAULT ''",
    "run_source": "VARCHAR(32) DEFAULT ''",
}


class TemplateStore:
    def __init__(self, db_path=REQUESTS_DB_PATH) -> None:
        ensure_data_dir()
        self._engine = create_engine(f"sqlite:///{db_path.resolve()}", future=True)
        Base.metadata.create_all(self._engine)
        self._migrate_request_columns()
        self._session_factory = sessionmaker(self._engine, expire_on_commit=False)

    def _migrate_request_columns(self) -> None:
        from .request_store import Base as RequestBase, RequestRecord

        RequestBase.metadata.create_all(self._engine)
        insp = inspect(self._engine)
        if "requests" not in insp.get_table_names():
            return
        existing = {c["name"] for c in insp.get_columns("requests")}
        with self._engine.begin() as conn:
            for name, ddl in _REQUEST_EXTRA_COLUMNS.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE requests ADD COLUMN {name} {ddl}"))

    def _session(self) -> Session:
        return self._session_factory()

    def list_templates(self, user_id: str) -> list[WorkflowTemplateRecord]:
        from sqlalchemy import select

        with self._session() as db:
            rows = db.execute(
                select(WorkflowTemplateRecord)
                .where(WorkflowTemplateRecord.user_id == user_id)
                .order_by(WorkflowTemplateRecord.name)
            ).scalars()
            return list(rows.all())

    def get_template(self, template_id: str) -> WorkflowTemplateRecord | None:
        with self._session() as db:
            return db.get(WorkflowTemplateRecord, template_id)

    def create_template(
        self,
        *,
        user_id: str,
        name: str,
        description_template: str,
        agent_type: str,
        agent_topology: str,
        default_priority: str,
        provider_id: str,
        model_id: str,
        require_plan_approval: bool,
        icon: str,
        category: str,
        bundled: bool = False,
    ) -> WorkflowTemplateRecord:
        now = datetime.now(timezone.utc)
        record = WorkflowTemplateRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            description_template=description_template,
            agent_type=agent_type,
            agent_topology=agent_topology,
            default_priority=default_priority,
            provider_id=provider_id,
            model_id=model_id,
            require_plan_approval=require_plan_approval,
            icon=icon,
            category=category,
            bundled=bundled,
            created_at=now,
            updated_at=now,
        )
        with self._session() as db:
            db.add(record)
            db.commit()
            db.refresh(record)
        return record

    def update_template(self, template_id: str, **fields: object) -> WorkflowTemplateRecord | None:
        with self._session() as db:
            record = db.get(WorkflowTemplateRecord, template_id)
            if record is None:
                return None
            for key, value in fields.items():
                if hasattr(record, key) and value is not None:
                    setattr(record, key, value)
            record.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(record)
            return record

    def delete_template(self, template_id: str) -> bool:
        with self._session() as db:
            record = db.get(WorkflowTemplateRecord, template_id)
            if record is None:
                return False
            db.delete(record)
            db.commit()
            return True

    def find_bundled_by_name(self, user_id: str, name: str) -> WorkflowTemplateRecord | None:
        from sqlalchemy import select

        with self._session() as db:
            return db.execute(
                select(WorkflowTemplateRecord).where(
                    WorkflowTemplateRecord.user_id == user_id,
                    WorkflowTemplateRecord.name == name,
                    WorkflowTemplateRecord.bundled.is_(True),
                )
            ).scalar_one_or_none()

    def list_schedules(self, user_id: str) -> list[WorkflowScheduleRecord]:
        from sqlalchemy import select

        with self._session() as db:
            rows = db.execute(
                select(WorkflowScheduleRecord)
                .where(WorkflowScheduleRecord.user_id == user_id)
                .order_by(WorkflowScheduleRecord.created_at.desc())
            ).scalars()
            return list(rows.all())

    def list_schedules_for_template(self, template_id: str) -> list[WorkflowScheduleRecord]:
        from sqlalchemy import select

        with self._session() as db:
            rows = db.execute(
                select(WorkflowScheduleRecord).where(
                    WorkflowScheduleRecord.template_id == template_id
                )
            ).scalars()
            return list(rows.all())

    def get_schedule(self, schedule_id: str) -> WorkflowScheduleRecord | None:
        with self._session() as db:
            return db.get(WorkflowScheduleRecord, schedule_id)

    def create_schedule(
        self,
        *,
        user_id: str,
        template_id: str,
        cron_expression: str,
        tz_name: str,
        enabled: bool,
        description_vars: str,
        on_approval: str,
        next_run_at: datetime | None,
    ) -> WorkflowScheduleRecord:
        now = datetime.now(timezone.utc)
        record = WorkflowScheduleRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            template_id=template_id,
            cron_expression=cron_expression,
            timezone=tz_name,
            enabled=enabled,
            description_vars=description_vars,
            on_approval=on_approval,
            last_run_at=None,
            next_run_at=next_run_at,
            last_request_id="",
            created_at=now,
            updated_at=now,
        )
        with self._session() as db:
            db.add(record)
            db.commit()
            db.refresh(record)
        return record

    def update_schedule(self, schedule_id: str, **fields: object) -> WorkflowScheduleRecord | None:
        with self._session() as db:
            record = db.get(WorkflowScheduleRecord, schedule_id)
            if record is None:
                return None
            for key, value in fields.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            record.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(record)
            return record

    def delete_schedule(self, schedule_id: str) -> bool:
        with self._session() as db:
            record = db.get(WorkflowScheduleRecord, schedule_id)
            if record is None:
                return False
            db.delete(record)
            db.commit()
            return True

    def list_enabled_schedules(self) -> list[WorkflowScheduleRecord]:
        from sqlalchemy import select

        with self._session() as db:
            rows = db.execute(
                select(WorkflowScheduleRecord).where(
                    WorkflowScheduleRecord.enabled.is_(True)
                )
            ).scalars()
            return list(rows.all())


def parse_json_field(raw: str, default: object) -> object:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default
