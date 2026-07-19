from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PanelConfig(Base):
    __tablename__ = "panel_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    panel_url: Mapped[str] = mapped_column(String(1024), default="")
    api_token_encrypted: Mapped[str] = mapped_column(Text, default="")
    subscription_template: Mapped[str] = mapped_column(
        String(2048), default=""
    )
    verify_tls: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_disable: Mapped[bool] = mapped_column(Boolean, default=True)
    engine_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    poll_interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    request_timeout_seconds: Mapped[int] = mapped_column(Integer, default=15)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ManagedUser(Base):
    __tablename__ = "managed_users"
    __table_args__ = (UniqueConstraint("email", name="uq_managed_users_email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(512), index=True)
    sub_id: Mapped[str] = mapped_column(String(512), default="")
    subscription_url: Mapped[str] = mapped_column(String(2048), default="")
    remote_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    remote_present: Mapped[bool] = mapped_column(Boolean, default=True)

    quota_bytes: Mapped[int] = mapped_column(Integer, default=0)
    enforcement_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    raw_upload_bytes: Mapped[int] = mapped_column(Integer, default=0)
    raw_download_bytes: Mapped[int] = mapped_column(Integer, default=0)
    raw_used_bytes: Mapped[int] = mapped_column(Integer, default=0)
    raw_total_bytes: Mapped[int] = mapped_column(Integer, default=0)
    last_raw_used_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cycle_used_bytes: Mapped[int] = mapped_column(Integer, default=0)
    cycle_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    disabled_by_ratio: Mapped[bool] = mapped_column(Boolean, default=False)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(16), default="info", index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    message: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(String(512), default="", index=True)
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
