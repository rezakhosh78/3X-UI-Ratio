from __future__ import annotations

import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.engine import make_url

from .config import settings
from .database import engine

REQUIRED_TABLES = {"panel_config", "managed_users", "audit_events"}
MAX_BACKUP_BYTES = 128 * 1024 * 1024


class BackupError(RuntimeError):
    pass


def database_path() -> Path:
    url = make_url(settings.database_url)
    if not url.drivername.startswith("sqlite") or not url.database:
        raise BackupError("Web backup and restore currently supports SQLite installations only.")
    path = Path(url.database)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path), timeout=30)
    connection.execute("PRAGMA busy_timeout=30000")
    return connection


def validate_backup(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise BackupError("The uploaded backup file is empty.")
    if path.stat().st_size > MAX_BACKUP_BYTES:
        raise BackupError("The uploaded backup exceeds the 128 MB limit.")
    with path.open("rb") as handle:
        if handle.read(16) != b"SQLite format 3\x00":
            raise BackupError("The uploaded file is not a valid SQLite database.")
    try:
        with _connect(path) as connection:
            result = connection.execute("PRAGMA quick_check").fetchone()
            if not result or result[0] != "ok":
                raise BackupError(f"SQLite integrity check failed: {result[0] if result else 'unknown error'}")
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            missing = sorted(REQUIRED_TABLES - tables)
            if missing:
                raise BackupError("The backup is missing required tables: " + ", ".join(missing))
    except sqlite3.DatabaseError as exc:
        raise BackupError(f"The uploaded backup could not be read: {exc}") from exc


def create_snapshot(destination: Path | None = None) -> Path:
    source_path = database_path()
    source_path.parent.mkdir(parents=True, exist_ok=True)
    if not source_path.exists():
        raise BackupError("The Ratio database does not exist yet.")

    if destination is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        fd, tmp_name = tempfile.mkstemp(prefix=f"3xui-ratio-{stamp}-", suffix=".sqlite3")
        os.close(fd)
        destination = Path(tmp_name)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        with _connect(source_path) as source, _connect(destination) as target:
            source.backup(target)
        validate_backup(destination)
        os.chmod(destination, 0o600)
        return destination
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def create_restore_point() -> Path:
    backup_dir = database_path().parent / "backups"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return create_snapshot(backup_dir / f"pre-restore-{stamp}.sqlite3")


def restore_snapshot(source_path: Path) -> Path:
    validate_backup(source_path)
    destination = database_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    restore_point = create_restore_point()

    engine.dispose()
    try:
        with _connect(source_path) as source, _connect(destination) as target:
            source.backup(target)
            target.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        validate_backup(destination)
    except Exception as exc:
        # Roll back to the automatically-created restore point.
        with _connect(restore_point) as source, _connect(destination) as target:
            source.backup(target)
        raise BackupError(f"Restore failed and the previous database was recovered: {exc}") from exc
    finally:
        engine.dispose()
        for suffix in ("-wal", "-shm"):
            Path(str(destination) + suffix).unlink(missing_ok=True)

    return restore_point
