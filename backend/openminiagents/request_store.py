"""SQLite index of UI-facing request metadata."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .config import REQUESTS_DB_PATH, ensure_data_dir


class Base(DeclarativeBase):
    pass


class RequestRecord(Base):
    __tablename__ = "requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    session_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    agent_type: Mapped[str] = mapped_column(String(32), default="workflow")
    llm_provider_id: Mapped[str] = mapped_column(String(32), default="")
    llm_model_id: Mapped[str] = mapped_column(String(64), default="")
    llm_display_name: Mapped[str] = mapped_column(String(128), default="")
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(16), default="normal")
    file_path: Mapped[str] = mapped_column(Text, default="")
    file_name: Mapped[str] = mapped_column(String(255), default="")
    sheet_url: Mapped[str] = mapped_column(Text, default="")
    current_step: Mapped[str] = mapped_column(String(64), default="SUBMITTED")
    status: Mapped[str] = mapped_column(String(32), default="active")
    status_message: Mapped[str] = mapped_column(Text, default="")
    latest_output: Mapped[str] = mapped_column(Text, default="")
    enabled_generic_agents: Mapped[str] = mapped_column(Text, default="[]")
    agent_topology: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


_EXTRA_COLUMNS = {
    "agent_type": "VARCHAR(32) DEFAULT 'workflow'",
    "file_path": "TEXT DEFAULT ''",
    "file_name": "VARCHAR(255) DEFAULT ''",
    "sheet_url": "TEXT DEFAULT ''",
    "llm_provider_id": "VARCHAR(32) DEFAULT ''",
    "llm_model_id": "VARCHAR(64) DEFAULT ''",
    "llm_display_name": "VARCHAR(128) DEFAULT ''",
    "enabled_generic_agents": "TEXT DEFAULT '[]'",
    "agent_topology": "TEXT DEFAULT ''",
}


class RequestStore:
    def __init__(self, db_path=REQUESTS_DB_PATH) -> None:
        ensure_data_dir()
        self._engine = create_engine(f"sqlite:///{db_path.resolve()}", future=True)
        Base.metadata.create_all(self._engine)
        self._migrate_columns()
        self._session_factory = sessionmaker(self._engine, expire_on_commit=False)

    def _migrate_columns(self) -> None:
        insp = inspect(self._engine)
        if "requests" not in insp.get_table_names():
            return
        existing = {c["name"] for c in insp.get_columns("requests")}
        with self._engine.begin() as conn:
            for name, ddl in _EXTRA_COLUMNS.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE requests ADD COLUMN {name} {ddl}"))

    def create(
        self,
        *,
        user_id: str,
        session_id: str,
        title: str,
        description: str,
        priority: str,
        agent_type: str = "workflow",
        file_path: str = "",
        file_name: str = "",
        sheet_url: str = "",
        llm_provider_id: str = "",
        llm_model_id: str = "",
        llm_display_name: str = "",
        enabled_generic_agents: str = "[]",
        agent_topology: str = "",
        current_step: str = "SUBMITTED",
        status_message: str = "Request submitted.",
    ) -> RequestRecord:
        now = datetime.now(timezone.utc)
        record = RequestRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            agent_type=agent_type,
            llm_provider_id=llm_provider_id,
            llm_model_id=llm_model_id,
            llm_display_name=llm_display_name,
            title=title,
            description=description,
            priority=priority,
            file_path=file_path,
            file_name=file_name,
            sheet_url=sheet_url,
            current_step=current_step,
            status="active",
            status_message=status_message,
            latest_output="",
            enabled_generic_agents=enabled_generic_agents,
            agent_topology=agent_topology,
            created_at=now,
            updated_at=now,
        )
        with self._session() as db:
            db.add(record)
            db.commit()
            db.refresh(record)
        return record

    def get(self, request_id: str) -> RequestRecord | None:
        with self._session() as db:
            return db.get(RequestRecord, request_id)

    def list_for_user(self, user_id: str) -> list[RequestRecord]:
        with self._session() as db:
            from sqlalchemy import select

            rows = db.execute(
                select(RequestRecord)
                .where(RequestRecord.user_id == user_id)
                .order_by(RequestRecord.created_at.desc())
            ).scalars()
            return list(rows.all())

    def update_from_session_state(
        self,
        request_id: str,
        *,
        current_step: str | None = None,
        status_message: str | None = None,
        latest_output: str | None = None,
        status: str | None = None,
    ) -> RequestRecord | None:
        with self._session() as db:
            record = db.get(RequestRecord, request_id)
            if record is None:
                return None
            if current_step is not None:
                record.current_step = current_step
            if status_message is not None:
                record.status_message = status_message
            if latest_output is not None:
                record.latest_output = latest_output
            if status is not None:
                record.status = status
            record.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(record)
            return record

    def _session(self) -> Session:
        return self._session_factory()
