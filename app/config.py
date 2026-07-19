from __future__ import annotations

import base64
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    admin_username: str
    admin_password: str
    session_secret: str
    encryption_key: str
    database_url: str
    cookie_secure: bool
    trusted_hosts: list[str]
    sync_default_interval: int


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    session_secret = os.getenv("SESSION_SECRET", "").strip()
    encryption_key = os.getenv("ENCRYPTION_KEY", "").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
    admin_password_b64 = os.getenv("ADMIN_PASSWORD_B64", "").strip()
    if admin_password_b64:
        try:
            admin_password = base64.b64decode(admin_password_b64, validate=True).decode("utf-8")
        except Exception as exc:
            raise RuntimeError("ADMIN_PASSWORD_B64 is invalid") from exc
    if len(session_secret) < 32:
        raise RuntimeError("SESSION_SECRET must contain at least 32 characters")
    if not encryption_key:
        raise RuntimeError("ENCRYPTION_KEY is required")
    if len(admin_password) < 8:
        raise RuntimeError("ADMIN_PASSWORD must contain at least 8 characters")

    trusted = [item.strip() for item in os.getenv("TRUSTED_HOSTS", "*").split(",") if item.strip()]
    interval = max(10, int(os.getenv("SYNC_DEFAULT_INTERVAL", "60")))
    return Settings(
        admin_username=os.getenv("ADMIN_USERNAME", "admin").strip() or "admin",
        admin_password=admin_password,
        session_secret=session_secret,
        encryption_key=encryption_key,
        database_url=os.getenv("DATABASE_URL", "sqlite:////data/ratio.db"),
        cookie_secure=_as_bool(os.getenv("COOKIE_SECURE"), False),
        trusted_hosts=trusted or ["*"],
        sync_default_interval=interval,
    )


settings = load_settings()
