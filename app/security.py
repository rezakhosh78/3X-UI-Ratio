from __future__ import annotations

import hmac
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, Request, status

from .config import settings


_fernet = Fernet(settings.encryption_key.encode("utf-8"))


def encrypt_secret(value: str) -> str:
    if not value:
        return ""
    return _fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    if not value:
        return ""
    try:
        return _fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("Stored API token cannot be decrypted") from exc


def credentials_valid(username: str, password: str) -> bool:
    return hmac.compare_digest(username, settings.admin_username) and hmac.compare_digest(
        password, settings.admin_password
    )


def require_login(request: Request) -> None:
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


def verify_same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        return
    parsed = urlparse(origin)
    request_host = request.headers.get("host", "")
    if parsed.netloc != request_host:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid origin")
