from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
import os
import tempfile

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .backup import BackupError, MAX_BACKUP_BYTES, create_snapshot, restore_snapshot
from .config import settings
from .database import Base, SessionLocal, engine, get_db
from .models import AuditEvent, ManagedUser, PanelConfig
from .schemas import BulkEnforcementInput, BulkQuotaInput, EngineInput, EnforcementInput, PanelConfigInput, QuotaInput
from .security import (
    credentials_valid,
    decrypt_secret,
    encrypt_secret,
    require_login,
    verify_same_origin,
)
from .sync import audit, now_utc, sync_service
from .xui import (
    XUIClient,
    XUIError,
    fetch_subscription_usage_from_candidates,
    normalize_panel_url,
    subscription_url_candidates,
)

BASE_DIR = Path(__file__).resolve().parent
VERSION = (BASE_DIR.parent / "VERSION").read_text(encoding="utf-8").strip()


def ensure_database() -> None:
    Base.metadata.create_all(bind=engine)

    # Preserve existing installations: create_all() does not add columns to an
    # already-created SQLite table, so apply the small in-place migration here.
    if settings.database_url.startswith("sqlite"):
        with engine.begin() as connection:
            columns = {
                row[1]
                for row in connection.execute(text("PRAGMA table_info(panel_config)"))
            }
            if "engine_enabled" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE panel_config "
                        "ADD COLUMN engine_enabled BOOLEAN NOT NULL DEFAULT 1"
                    )
                )

            user_columns = {
                row[1]
                for row in connection.execute(text("PRAGMA table_info(managed_users)"))
            }
            if "raw_total_bytes" not in user_columns:
                connection.execute(
                    text(
                        "ALTER TABLE managed_users "
                        "ADD COLUMN raw_total_bytes INTEGER NOT NULL DEFAULT 0"
                    )
                )

    with SessionLocal() as db:
        cfg = db.get(PanelConfig, 1)
        if cfg is None:
            db.add(
                PanelConfig(
                    id=1,
                    poll_interval_seconds=settings.sync_default_interval,
                    engine_enabled=True,
                )
            )
            db.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_database()
    sync_service.start()
    yield
    await sync_service.stop()


app = FastAPI(title="3X-UI Ratio", version=VERSION, docs_url=None, redoc_url=None, lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    https_only=settings.cookie_secure,
    max_age=60 * 60 * 12,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def api_guard(request: Request) -> None:
    require_login(request)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        verify_same_origin(request)


def operational_guard() -> None:
    """Block all operational Ratio actions while the master switch is paused."""
    with SessionLocal() as db:
        cfg = db.get(PanelConfig, 1)
        if not cfg or not cfg.engine_enabled:
            raise HTTPException(
                status_code=409,
                detail=(
                    "3X-UI Ratio is paused. Turn the master switch on before running "
                    "synchronization, traffic reads, quota operations, connection tests, "
                    "or client status changes."
                ),
            )


def user_dict(user: ManagedUser) -> dict:
    quota = max(0, user.quota_bytes)
    used = max(0, user.cycle_used_bytes)
    remaining = max(0, quota - used) if quota else 0
    percent = min(100.0, (used / quota * 100.0)) if quota else 0.0
    return {
        "id": user.id,
        "email": user.email,
        "sub_id": user.sub_id,
        "subscription_url": user.subscription_url,
        "remote_enabled": user.remote_enabled,
        "remote_present": user.remote_present,
        "quota_bytes": quota,
        "raw_upload_bytes": user.raw_upload_bytes,
        "raw_download_bytes": user.raw_download_bytes,
        "raw_used_bytes": user.raw_used_bytes,
        "raw_total_bytes": user.raw_total_bytes,
        "raw_percent": min(100.0, (user.raw_used_bytes / user.raw_total_bytes * 100.0)) if user.raw_total_bytes else 0.0,
        "cycle_used_bytes": used,
        "remaining_bytes": remaining,
        "percent": percent,
        "enforcement_enabled": user.enforcement_enabled,
        "disabled_by_ratio": user.disabled_by_ratio,
        "disabled_at": user.disabled_at.isoformat() if user.disabled_at else None,
        "last_checked_at": user.last_checked_at.isoformat() if user.last_checked_at else None,
        "last_success_at": user.last_success_at.isoformat() if user.last_success_at else None,
        "last_error": user.last_error,
    }


@app.exception_handler(XUIError)
async def xui_error_handler(_request: Request, exc: XUIError):
    return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "3X-UI Ratio", "version": VERSION}


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("authenticated"):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"version": VERSION, "error": ""})


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    verify_same_origin(request)
    if not credentials_valid(username.strip(), password):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"version": VERSION, "error": "Incorrect username or password."},
            status_code=401,
        )
    request.session.clear()
    request.session["authenticated"] = True
    request.session["username"] = username.strip()
    return RedirectResponse("/", status_code=303)


@app.post("/logout")
def logout(request: Request):
    require_login(request)
    verify_same_origin(request)
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    if not request.session.get("authenticated"):
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(
        request,
        "index.html",
        {"version": VERSION, "username": request.session.get("username", "admin")},
    )


@app.get("/api/overview", dependencies=[Depends(api_guard)])
def overview(db: Session = Depends(get_db)) -> dict:
    cfg = db.get(PanelConfig, 1)
    total = db.scalar(select(func.count()).select_from(ManagedUser).where(ManagedUser.remote_present.is_(True))) or 0
    enabled = db.scalar(
        select(func.count()).select_from(ManagedUser).where(ManagedUser.remote_present.is_(True), ManagedUser.remote_enabled.is_(True))
    ) or 0
    enforced = db.scalar(
        select(func.count()).select_from(ManagedUser).where(ManagedUser.remote_present.is_(True), ManagedUser.enforcement_enabled.is_(True))
    ) or 0
    exhausted = db.scalar(
        select(func.count()).select_from(ManagedUser).where(
            ManagedUser.remote_present.is_(True),
            ManagedUser.quota_bytes > 0,
            ManagedUser.cycle_used_bytes >= ManagedUser.quota_bytes,
        )
    ) or 0
    return {
        "ok": True,
        "version": VERSION,
        "stats": {"total": total, "enabled": enabled, "enforced": enforced, "exhausted": exhausted},
        "config": {
            "configured": bool(cfg and cfg.panel_url and cfg.api_token_encrypted),
            "panel_url": cfg.panel_url if cfg else "",
            "subscription_template": cfg.subscription_template if cfg else "",
            "verify_tls": cfg.verify_tls if cfg else True,
            "auto_disable": cfg.auto_disable if cfg else True,
            "engine_enabled": cfg.engine_enabled if cfg else True,
            "poll_interval_seconds": cfg.poll_interval_seconds if cfg else 60,
            "request_timeout_seconds": cfg.request_timeout_seconds if cfg else 15,
            "last_sync_at": cfg.last_sync_at.isoformat() if cfg and cfg.last_sync_at else None,
            "last_sync_ok": cfg.last_sync_ok if cfg else False,
            "last_error": cfg.last_error if cfg else "",
            "token_saved": bool(cfg and cfg.api_token_encrypted),
        },
    }


@app.get("/api/users", dependencies=[Depends(api_guard)])
def users(q: str = "", db: Session = Depends(get_db)) -> dict:
    statement = select(ManagedUser).where(ManagedUser.remote_present.is_(True)).order_by(ManagedUser.email.asc())
    if q.strip():
        statement = statement.where(ManagedUser.email.ilike(f"%{q.strip()}%"))
    rows = db.scalars(statement).all()
    return {"ok": True, "users": [user_dict(item) for item in rows]}


@app.post("/api/config", dependencies=[Depends(api_guard)])
def save_config(payload: PanelConfigInput, db: Session = Depends(get_db)) -> dict:
    cfg = db.get(PanelConfig, 1) or PanelConfig(id=1)
    cfg.panel_url = normalize_panel_url(payload.panel_url)
    if payload.api_token.strip():
        cfg.api_token_encrypted = encrypt_secret(payload.api_token.strip())
    elif not cfg.api_token_encrypted:
        raise HTTPException(status_code=422, detail="API token is required")
    cfg.subscription_template = payload.subscription_template.strip()
    cfg.verify_tls = payload.verify_tls
    cfg.auto_disable = payload.auto_disable
    cfg.poll_interval_seconds = payload.poll_interval_seconds
    cfg.request_timeout_seconds = payload.request_timeout_seconds
    db.add(cfg)
    audit(db, "info", "config_saved", "Panel connection settings were saved.")
    db.commit()
    sync_service.reschedule(immediate=True)
    return {"ok": True}


@app.post("/api/config/test", dependencies=[Depends(api_guard), Depends(operational_guard)])
async def test_config(payload: PanelConfigInput, db: Session = Depends(get_db)) -> dict:
    cfg = db.get(PanelConfig, 1)
    token = payload.api_token.strip()
    if not token and cfg and cfg.api_token_encrypted:
        token = decrypt_secret(cfg.api_token_encrypted)
    if not token:
        raise XUIError("API token is required.")
    xui = XUIClient(
        payload.panel_url,
        token,
        verify_tls=payload.verify_tls,
        timeout=payload.request_timeout_seconds,
    )
    clients = await xui.list_clients()
    sample = next((item for item in clients if item.sub_id), None)
    subscription_test = None
    if sample is not None:
        candidates = subscription_url_candidates(
            payload.subscription_template,
            payload.panel_url,
            sample.sub_id,
            sample.email,
            sample.subscription_url,
        )
        usage, working_url = await fetch_subscription_usage_from_candidates(
            candidates,
            verify_tls=payload.verify_tls,
            timeout=payload.request_timeout_seconds,
        )
        subscription_test = {
            "email": sample.email,
            "url": working_url,
            "used_bytes": usage.used,
        }
    return {
        "ok": True,
        "client_count": len(clients),
        "subscription_test": subscription_test,
    }


@app.post("/api/sync", dependencies=[Depends(api_guard), Depends(operational_guard)])
async def sync_now() -> dict:
    result = await sync_service.run_once(trigger="manual")
    return {"ok": True, "result": result}


@app.post("/api/engine", dependencies=[Depends(api_guard)])
def set_engine(payload: EngineInput, db: Session = Depends(get_db)) -> dict:
    cfg = db.get(PanelConfig, 1) or PanelConfig(id=1)
    cfg.engine_enabled = payload.enabled
    db.add(cfg)
    audit(
        db,
        "info" if payload.enabled else "warning",
        "engine_enabled" if payload.enabled else "engine_disabled",
        "Ratio engine was enabled." if payload.enabled else "Ratio engine was disabled.",
    )
    db.commit()
    sync_service.reschedule(immediate=payload.enabled)
    return {"ok": True, "engine_enabled": cfg.engine_enabled}


def _apply_quota(user: ManagedUser, quota_gb: float, enforcement_enabled: bool, reset_cycle: bool) -> None:
    user.quota_bytes = int(quota_gb * 1024**3)
    user.enforcement_enabled = enforcement_enabled and user.quota_bytes > 0
    if reset_cycle:
        user.cycle_used_bytes = 0
        user.last_raw_used_bytes = user.raw_used_bytes if user.last_success_at else None
        user.cycle_started_at = now_utc()
        user.disabled_by_ratio = False
        user.disabled_at = None


@app.post("/api/users/bulk-quota", dependencies=[Depends(api_guard), Depends(operational_guard)])
def set_bulk_quota(payload: BulkQuotaInput, db: Session = Depends(get_db)) -> dict:
    users = db.scalars(
        select(ManagedUser).where(
            ManagedUser.id.in_(payload.user_ids),
            ManagedUser.remote_present.is_(True),
        )
    ).all()
    if not users:
        raise HTTPException(status_code=404, detail="No active selected users were found")

    for user in users:
        _apply_quota(
            user,
            payload.quota_gb,
            payload.enforcement_enabled,
            payload.reset_cycle,
        )

    quota_bytes = int(payload.quota_gb * 1024**3)
    audit(
        db,
        "info",
        "bulk_quota_changed",
        "Ratio quota was updated for selected users.",
        details={
            "updated_count": len(users),
            "requested_count": len(payload.user_ids),
            "quota_bytes": quota_bytes,
            "reset_cycle": payload.reset_cycle,
            "enforcement_enabled": payload.enforcement_enabled and quota_bytes > 0,
        },
    )
    db.commit()
    return {
        "ok": True,
        "updated": len(users),
        "skipped": max(0, len(payload.user_ids) - len(users)),
    }


@app.post("/api/enforcement/start-selected", dependencies=[Depends(api_guard), Depends(operational_guard)])
def start_selected_enforcement(payload: BulkEnforcementInput, db: Session = Depends(get_db)) -> dict:
    users = db.scalars(
        select(ManagedUser).where(
            ManagedUser.id.in_(payload.user_ids),
            ManagedUser.remote_present.is_(True),
        )
    ).all()
    if not users:
        raise HTTPException(status_code=404, detail="No active selected users were found")

    updated = 0
    skipped_no_quota = 0
    for user in users:
        if user.quota_bytes <= 0:
            skipped_no_quota += 1
            continue
        if not user.enforcement_enabled:
            user.enforcement_enabled = True
            updated += 1

    audit(
        db,
        "info",
        "selected_enforcement_started",
        "Quota enforcement was started for selected users.",
        details={
            "updated_count": updated,
            "requested_count": len(payload.user_ids),
            "skipped_no_quota": skipped_no_quota,
            "skipped_missing": max(0, len(payload.user_ids) - len(users)),
        },
    )
    db.commit()
    return {
        "ok": True,
        "updated": updated,
        "skipped_no_quota": skipped_no_quota,
        "skipped_missing": max(0, len(payload.user_ids) - len(users)),
    }


@app.post("/api/enforcement/stop-all", dependencies=[Depends(api_guard), Depends(operational_guard)])
def stop_all_enforcement(db: Session = Depends(get_db)) -> dict:
    users = db.scalars(
        select(ManagedUser).where(
            ManagedUser.remote_present.is_(True),
            ManagedUser.enforcement_enabled.is_(True),
        )
    ).all()
    for user in users:
        user.enforcement_enabled = False

    audit(
        db,
        "warning",
        "all_enforcement_stopped",
        "Quota enforcement was stopped for all active Ratio users.",
        details={"updated_count": len(users)},
    )
    db.commit()
    return {"ok": True, "updated": len(users)}


@app.post("/api/users/{user_id}/quota", dependencies=[Depends(api_guard), Depends(operational_guard)])
def set_quota(user_id: int, payload: QuotaInput, db: Session = Depends(get_db)) -> dict:
    user = db.get(ManagedUser, user_id)
    if user is None or not user.remote_present:
        raise HTTPException(status_code=404, detail="Active user not found")
    _apply_quota(user, payload.quota_gb, payload.enforcement_enabled, payload.reset_cycle)
    audit(
        db,
        "info",
        "quota_changed",
        "Ratio quota was updated.",
        user.email,
        {"quota_bytes": user.quota_bytes, "reset_cycle": payload.reset_cycle},
    )
    db.commit()
    return {"ok": True, "user": user_dict(user)}


@app.post("/api/users/{user_id}/reset-cycle", dependencies=[Depends(api_guard), Depends(operational_guard)])
def reset_cycle(user_id: int, db: Session = Depends(get_db)) -> dict:
    user = db.get(ManagedUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.cycle_used_bytes = 0
    user.last_raw_used_bytes = user.raw_used_bytes
    user.cycle_started_at = now_utc()
    user.disabled_by_ratio = False
    user.disabled_at = None
    audit(db, "info", "cycle_reset", "Ratio usage cycle was reset.", user.email)
    db.commit()
    return {"ok": True, "user": user_dict(user)}


@app.post("/api/users/{user_id}/enforcement", dependencies=[Depends(api_guard), Depends(operational_guard)])
def set_enforcement(user_id: int, payload: EnforcementInput, db: Session = Depends(get_db)) -> dict:
    user = db.get(ManagedUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.enforcement_enabled = payload.enabled and user.quota_bytes > 0
    audit(
        db,
        "info",
        "enforcement_changed",
        "Quota enforcement setting was updated.",
        user.email,
        {"enabled": user.enforcement_enabled},
    )
    db.commit()
    return {"ok": True, "user": user_dict(user)}


async def _change_remote_user(user_id: int, enabled: bool, db: Session) -> dict:
    cfg = db.get(PanelConfig, 1)
    user = db.get(ManagedUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not cfg or not cfg.panel_url or not cfg.api_token_encrypted:
        raise XUIError("Panel connection settings are incomplete.")
    xui = XUIClient(
        cfg.panel_url,
        decrypt_secret(cfg.api_token_encrypted),
        verify_tls=cfg.verify_tls,
        timeout=cfg.request_timeout_seconds,
    )
    await xui.set_enabled([user.email], enabled)
    verified = {item.email: item for item in await xui.list_clients()}
    remote = verified.get(user.email)
    if remote is None or remote.enabled != enabled:
        raise XUIError("3X-UI did not confirm the client status change.")
    user.remote_enabled = enabled
    if enabled:
        # Prevent the worker from immediately disabling an already exhausted user.
        user.enforcement_enabled = False
        user.disabled_by_ratio = False
        user.disabled_at = None
    else:
        user.disabled_by_ratio = False
        user.disabled_at = now_utc()
    audit(
        db,
        "warning" if not enabled else "info",
        "manual_enable" if enabled else "manual_disable",
        "Client was enabled manually." if enabled else "Client was disabled manually.",
        user.email,
    )
    db.commit()
    return {"ok": True, "user": user_dict(user)}


@app.post("/api/users/{user_id}/disable", dependencies=[Depends(api_guard), Depends(operational_guard)])
async def disable_user(user_id: int, db: Session = Depends(get_db)) -> dict:
    return await _change_remote_user(user_id, False, db)


@app.post("/api/users/{user_id}/enable", dependencies=[Depends(api_guard), Depends(operational_guard)])
async def enable_user(user_id: int, db: Session = Depends(get_db)) -> dict:
    return await _change_remote_user(user_id, True, db)


@app.get("/api/events", dependencies=[Depends(api_guard)])
def events(limit: int = 100, db: Session = Depends(get_db)) -> dict:
    limit = min(500, max(1, limit))
    rows = db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)).all()
    return {
        "ok": True,
        "events": [
            {
                "id": item.id,
                "level": item.level,
                "action": item.action,
                "message": item.message,
                "email": item.email,
                "details": json.loads(item.details or "{}"),
                "created_at": item.created_at.isoformat(),
            }
            for item in rows
        ],
    }


@app.exception_handler(BackupError)
async def backup_error_handler(_request: Request, exc: BackupError):
    return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})


def _remove_file(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


@app.post("/api/database/backup", dependencies=[Depends(api_guard)])
async def download_database_backup() -> FileResponse:
    async with sync_service.lock:
        snapshot = create_snapshot()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return FileResponse(
        path=snapshot,
        media_type="application/vnd.sqlite3",
        filename=f"3xui-ratio-{stamp}.sqlite3",
        background=BackgroundTask(_remove_file, str(snapshot)),
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/database/restore", dependencies=[Depends(api_guard)])
async def restore_database_backup(backup: UploadFile = File(...)) -> dict:
    filename = backup.filename or "backup.sqlite3"
    if not filename.lower().endswith((".sqlite", ".sqlite3", ".db")):
        raise BackupError("Select a .sqlite, .sqlite3, or .db backup file.")

    fd, temp_name = tempfile.mkstemp(prefix="3xui-ratio-upload-", suffix=".sqlite3")
    os.close(fd)
    temp_path = Path(temp_name)
    total = 0
    try:
        with temp_path.open("wb") as destination:
            while chunk := await backup.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_BACKUP_BYTES:
                    raise BackupError("The uploaded backup exceeds the 128 MB limit.")
                destination.write(chunk)
        async with sync_service.lock:
            restore_point = restore_snapshot(temp_path)
            ensure_database()
            with SessionLocal() as db:
                audit(
                    db,
                    "warning",
                    "database_restored",
                    "Ratio database was restored from a Web UI backup.",
                    details={
                        "uploaded_filename": filename,
                        "restore_point": str(restore_point),
                    },
                )
                db.commit()
        return {
            "ok": True,
            "message": "Database restored successfully.",
            "restore_point": restore_point.name,
        }
    finally:
        await backup.close()
        temp_path.unlink(missing_ok=True)
