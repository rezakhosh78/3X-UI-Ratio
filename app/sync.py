from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone

from sqlalchemy import select

from .database import SessionLocal
from .metering import update_cycle_meter
from .models import AuditEvent, ManagedUser, PanelConfig
from .security import decrypt_secret
from .xui import (
    XUIClient,
    XUIError,
    fetch_subscription_usage_from_candidates,
    subscription_url_candidates,
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def audit(db, level: str, action: str, message: str, email: str = "", details: dict | None = None) -> None:
    db.add(
        AuditEvent(
            level=level,
            action=action,
            message=message,
            email=email,
            details=json.dumps(details or {}, ensure_ascii=False),
        )
    )


class SyncService:
    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._wake = asyncio.Event()
        self._event_loop: asyncio.AbstractEventLoop | None = None
        self._run_immediately = False

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._event_loop = asyncio.get_running_loop()
            self._stop.clear()
            self._wake.clear()
            self._run_immediately = False
            self._task = asyncio.create_task(self._loop(), name="3xui-ratio-sync")

    async def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._event_loop = None

    def reschedule(self, *, immediate: bool = False) -> None:
        """Wake the scheduler safely after settings or engine changes."""
        if immediate:
            self._run_immediately = True
        loop = self._event_loop
        if loop and loop.is_running():
            loop.call_soon_threadsafe(self._wake.set)

    @staticmethod
    def _scheduler_config() -> tuple[int, bool, bool]:
        interval = 60
        enabled = False
        configured = False
        with SessionLocal() as db:
            cfg = db.get(PanelConfig, 1)
            if cfg:
                interval = max(10, int(cfg.poll_interval_seconds or 60))
                enabled = bool(cfg.engine_enabled)
                configured = bool(cfg.panel_url and cfg.api_token_encrypted)
        return interval, enabled, configured

    @staticmethod
    def _advance_deadline(scheduled_due: float, interval: int, now: float) -> float:
        next_due = scheduled_due + max(10, int(interval))
        while next_due <= now:
            next_due += max(10, int(interval))
        return next_due

    async def _wait_for_signal(self, timeout: float) -> str:
        stop_task = asyncio.create_task(self._stop.wait())
        wake_task = asyncio.create_task(self._wake.wait())
        done, pending = await asyncio.wait(
            {stop_task, wake_task},
            timeout=max(0.0, timeout),
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        if self._stop.is_set():
            return "stop"
        if wake_task in done and wake_task.result():
            self._wake.clear()
            return "wake"
        return "timeout"

    async def _loop(self) -> None:
        # Give the container a short startup window, then keep a monotonic fixed cadence.
        next_due = time.monotonic() + 5.0
        while not self._stop.is_set():
            interval, enabled, configured = self._scheduler_config()
            if self._run_immediately:
                self._run_immediately = False
                next_due = time.monotonic()

            signal = await self._wait_for_signal(next_due - time.monotonic())
            if signal == "stop":
                return
            if signal == "wake":
                # Re-read the latest interval and engine state without waiting for the old timeout.
                continue

            scheduled_due = next_due
            if enabled and configured:
                try:
                    await self.run_once(trigger="scheduler")
                except XUIError as exc:
                    if "already running" not in str(exc).lower():
                        pass
                except Exception:
                    pass

            # Advance from the scheduled deadline, not from sync completion, so runtime
            # does not accumulate drift. Missed slots are skipped rather than queued.
            now = time.monotonic()
            next_due = self._advance_deadline(scheduled_due, interval, now)

    async def run_once(self, trigger: str = "manual") -> dict:
        if self.lock.locked():
            raise XUIError("Another synchronization is already running.")
        async with self.lock:
            return await self._run_locked(trigger)

    async def _run_locked(self, trigger: str) -> dict:
        with SessionLocal() as db:
            cfg = db.get(PanelConfig, 1)
            if not cfg or not cfg.panel_url or not cfg.api_token_encrypted:
                raise XUIError("Configure the 3X-UI connection before synchronizing.")
            if not cfg.engine_enabled:
                raise XUIError("The Ratio engine is disabled. Enable it before synchronizing.")
            panel_url = cfg.panel_url
            token = decrypt_secret(cfg.api_token_encrypted)
            verify_tls = cfg.verify_tls
            timeout = cfg.request_timeout_seconds
            subscription_base = cfg.subscription_template
            auto_disable = cfg.auto_disable

        client = XUIClient(panel_url, token, verify_tls=verify_tls, timeout=timeout)
        try:
            remote_clients = await client.list_clients()
        except Exception as exc:
            self._record_sync_failure(str(exc), trigger)
            raise

        with SessionLocal() as db:
            current_cfg = db.get(PanelConfig, 1)
            if not current_cfg or not current_cfg.engine_enabled:
                raise XUIError(
                    "Ratio was paused while synchronization was running. "
                    "No user-list, usage, quota, or enforcement changes were applied."
                )

        removed_count = 0
        with SessionLocal() as db:
            existing = {u.email: u for u in db.scalars(select(ManagedUser)).all()}
            for user in existing.values():
                user.remote_present = False

            for remote in remote_clients:
                user = existing.get(remote.email)
                if user is None:
                    user = ManagedUser(email=remote.email, cycle_started_at=now_utc())
                    db.add(user)
                    existing[remote.email] = user
                user.sub_id = remote.sub_id
                user.remote_enabled = remote.enabled
                user.remote_present = True
                if remote.sub_id:
                    try:
                        candidates = subscription_url_candidates(
                            subscription_base,
                            panel_url,
                            remote.sub_id,
                            remote.email,
                            remote.subscription_url or user.subscription_url,
                        )
                        user.subscription_url = candidates[0]
                        user.last_error = ""
                    except XUIError as exc:
                        user.subscription_url = ""
                        user.last_error = str(exc)
                else:
                    user.subscription_url = ""
                    user.last_error = "Client has no subId in 3X-UI."

            for user in existing.values():
                if not user.remote_present:
                    removed_count += 1
                    user.subscription_url = ""
                    user.last_error = "Client no longer exists in 3X-UI."

            if removed_count:
                audit(
                    db,
                    "info",
                    "remote_users_removed",
                    "Clients removed from 3X-UI were hidden from the active Ratio user list.",
                    details={"count": removed_count},
                )
            db.commit()

        semaphore = asyncio.Semaphore(10)

        async def read_usage(email: str, urls: list[str]):
            async with semaphore:
                try:
                    usage, working_url = await fetch_subscription_usage_from_candidates(
                        urls,
                        verify_tls=verify_tls,
                        timeout=timeout,
                    )
                    return email, usage, working_url, None
                except Exception as exc:
                    return email, None, "", str(exc)

        jobs = []
        with SessionLocal() as db:
            for user in db.scalars(
                select(ManagedUser).where(ManagedUser.remote_present.is_(True))
            ).all():
                if user.sub_id:
                    try:
                        urls = subscription_url_candidates(
                            subscription_base,
                            panel_url,
                            user.sub_id,
                            user.email,
                            user.subscription_url,
                        )
                        jobs.append(read_usage(user.email, urls))
                    except XUIError as exc:
                        jobs.append(
                            asyncio.sleep(
                                0,
                                result=(user.email, None, "", str(exc)),
                            )
                        )
                else:
                    jobs.append(
                        asyncio.sleep(
                            0,
                            result=(
                                user.email,
                                None,
                                "",
                                user.last_error or "Client has no usable subscription URL.",
                            ),
                        )
                    )

        results = await asyncio.gather(*jobs) if jobs else []

        with SessionLocal() as db:
            current_cfg = db.get(PanelConfig, 1)
            if not current_cfg or not current_cfg.engine_enabled:
                raise XUIError(
                    "Ratio was paused while subscription traffic was being read. "
                    "No usage, quota, or enforcement changes were applied."
                )

        exceeded: list[str] = []
        successful = 0
        failed = 0

        with SessionLocal() as db:
            users = {u.email: u for u in db.scalars(select(ManagedUser)).all()}
            cfg = db.get(PanelConfig, 1)
            engine_still_enabled = bool(cfg and cfg.engine_enabled)
            for email, usage, working_url, error in results:
                user = users.get(email)
                if user is None or not user.remote_present:
                    continue
                user.last_checked_at = now_utc()
                if error or usage is None:
                    failed += 1
                    user.last_error = error or "Unknown subscription error."
                    continue

                successful += 1
                user.subscription_url = working_url
                user.raw_upload_bytes = usage.upload
                user.raw_download_bytes = usage.download
                user.raw_used_bytes = usage.used
                user.raw_total_bytes = usage.total
                meter = update_cycle_meter(
                    user.last_raw_used_bytes, user.cycle_used_bytes, usage.used
                )
                user.last_raw_used_bytes = meter.new_last_raw
                user.cycle_used_bytes = meter.new_cycle_used
                user.last_success_at = now_utc()
                user.last_error = ""
                if meter.reset_detected:
                    audit(
                        db,
                        "info",
                        "counter_reset",
                        "A source traffic counter reset was detected; the Ratio cycle was preserved.",
                        email,
                    )
                if (
                    engine_still_enabled
                    and auto_disable
                    and user.enforcement_enabled
                    and user.quota_bytes > 0
                    and user.cycle_used_bytes >= user.quota_bytes
                    and user.remote_enabled
                ):
                    exceeded.append(email)
            db.commit()

        disable_error = ""
        if exceeded:
            # Re-check the master switch immediately before a destructive remote action.
            with SessionLocal() as db:
                current_cfg = db.get(PanelConfig, 1)
                can_disable = bool(
                    current_cfg and current_cfg.engine_enabled and current_cfg.auto_disable
                )
            if can_disable:
                try:
                    await client.set_enabled(exceeded, False)
                    verified = {item.email: item for item in await client.list_clients()}
                    still_enabled = [
                        email
                        for email in exceeded
                        if verified.get(email) is None or verified[email].enabled
                    ]
                    if still_enabled:
                        raise XUIError(
                            "3X-UI did not confirm that these clients were disabled: "
                            + ", ".join(still_enabled[:5])
                        )
                    with SessionLocal() as db:
                        for user in db.scalars(
                            select(ManagedUser).where(ManagedUser.email.in_(exceeded))
                        ).all():
                            user.remote_enabled = False
                            user.disabled_by_ratio = True
                            user.disabled_at = now_utc()
                            audit(
                                db,
                                "warning",
                                "auto_disable",
                                "Client was disabled because the Ratio quota was exhausted.",
                                user.email,
                                {"quota": user.quota_bytes, "used": user.cycle_used_bytes},
                            )
                        db.commit()
                except Exception as exc:
                    disable_error = str(exc)
                    with SessionLocal() as db:
                        audit(
                            db,
                            "error",
                            "auto_disable_failed",
                            "Automatic client disabling failed.",
                            details={"emails": exceeded, "error": disable_error},
                        )
                        db.commit()
            else:
                exceeded = []

        with SessionLocal() as db:
            cfg = db.get(PanelConfig, 1)
            if cfg:
                cfg.last_sync_at = now_utc()
                cfg.last_sync_ok = not bool(disable_error) and failed == 0
                cfg.last_error = disable_error or (
                    f"{failed} subscription reads failed." if failed else ""
                )
            audit(
                db,
                "info" if not disable_error and failed == 0 else "warning",
                "sync",
                "Synchronization completed."
                if not disable_error and failed == 0
                else "Synchronization completed with errors.",
                details={
                    "trigger": trigger,
                    "remote_clients": len(remote_clients),
                    "removed_clients": removed_count,
                    "successful_subscriptions": successful,
                    "failed_subscriptions": failed,
                    "disabled": len(exceeded) if not disable_error else 0,
                    "disable_error": disable_error,
                    "api_root": client.discovered_api_root,
                },
            )
            db.commit()

        return {
            "remote_clients": len(remote_clients),
            "removed": removed_count,
            "successful": successful,
            "failed": failed,
            "disabled": len(exceeded) if not disable_error else 0,
            "disable_error": disable_error,
            "api_root": client.discovered_api_root,
        }

    @staticmethod
    def _record_sync_failure(error: str, trigger: str) -> None:
        with SessionLocal() as db:
            cfg = db.get(PanelConfig, 1)
            if cfg:
                cfg.last_sync_at = now_utc()
                cfg.last_sync_ok = False
                cfg.last_error = error
            audit(
                db,
                "error",
                "sync_failed",
                "Connection to 3X-UI failed.",
                details={"trigger": trigger, "error": error},
            )
            db.commit()


sync_service = SyncService()
