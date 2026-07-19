import base64
import os
from pathlib import Path

from cryptography.fernet import Fernet

os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD_B64", base64.b64encode(b"test-password").decode())
os.environ.setdefault("SESSION_SECRET", "s" * 64)
os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/3xui-ratio-test-bulk.db")
os.environ.setdefault("TRUSTED_HOSTS", "*")

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import set_bulk_quota, start_selected_enforcement, stop_all_enforcement  # noqa: E402
from app.models import ManagedUser, PanelConfig  # noqa: E402
from app.schemas import BulkEnforcementInput, BulkQuotaInput  # noqa: E402


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        db.add(PanelConfig(id=1, engine_enabled=True))
        db.add_all(
            [
                ManagedUser(email="alice", remote_present=True, enforcement_enabled=True),
                ManagedUser(email="bob", remote_present=True, enforcement_enabled=True),
                ManagedUser(email="archived", remote_present=False, enforcement_enabled=True),
            ]
        )
        db.commit()


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    Path("/tmp/3xui-ratio-test-bulk.db").unlink(missing_ok=True)


def test_bulk_quota_only_updates_active_selected_users():
    with SessionLocal() as db:
        users = {user.email: user for user in db.query(ManagedUser).all()}
        result = set_bulk_quota(
            BulkQuotaInput(
                user_ids=[users["alice"].id, users["bob"].id, users["archived"].id],
                quota_gb=10,
                enforcement_enabled=True,
                reset_cycle=True,
            ),
            db,
        )
        assert result["updated"] == 2
        assert result["skipped"] == 1
        db.expire_all()
        assert db.get(ManagedUser, users["alice"].id).quota_bytes == 10 * 1024**3
        assert db.get(ManagedUser, users["bob"].id).enforcement_enabled is True
        assert db.get(ManagedUser, users["archived"].id).quota_bytes == 0


def test_stop_all_enforcement_does_not_change_remote_status():
    with SessionLocal() as db:
        before = {user.email: user.remote_enabled for user in db.query(ManagedUser).all()}
        result = stop_all_enforcement(db)
        assert result["updated"] == 2
        db.expire_all()
        active = db.query(ManagedUser).filter(ManagedUser.remote_present.is_(True)).all()
        assert all(user.enforcement_enabled is False for user in active)
        after = {user.email: user.remote_enabled for user in db.query(ManagedUser).all()}
        assert after == before


def test_start_selected_enforcement_requires_existing_quota():
    with SessionLocal() as db:
        users = {user.email: user for user in db.query(ManagedUser).all()}
        users["alice"].quota_bytes = 5 * 1024**3
        users["alice"].enforcement_enabled = False
        users["bob"].quota_bytes = 0
        users["bob"].enforcement_enabled = False
        db.commit()
        result = start_selected_enforcement(
            BulkEnforcementInput(user_ids=[users["alice"].id, users["bob"].id]),
            db,
        )
        assert result["updated"] == 1
        assert result["skipped_no_quota"] == 1
        db.expire_all()
        assert db.get(ManagedUser, users["alice"].id).enforcement_enabled is True
        assert db.get(ManagedUser, users["bob"].id).enforcement_enabled is False
