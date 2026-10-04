"""Environment-configured admin/staff authentication for the local demo."""

import base64
import hashlib
import hmac
import json
import os
import time
import secrets
from pathlib import Path

from fastapi import HTTPException


def load_local_environment(local_env: Path | None = None) -> None:
    """Load backend/.env for local runs without replacing shell settings."""
    if local_env is None:
        local_env = Path(__file__).resolve().parents[1] / ".env"
    if not local_env.is_file():
        return
    for line in local_env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)


load_local_environment()


def _secret() -> bytes:
    return os.getenv("ADMIN_TOKEN_SECRET", "").encode()


def _credentials() -> dict[str, tuple[str, str]]:
    return {
        "admin": (
            os.getenv("ADMIN_EMAIL", ""),
            os.getenv("ADMIN_PASSWORD", ""),
        ),
        "staff": (
            os.getenv("STAFF_EMAIL", ""),
            os.getenv("STAFF_PASSWORD", ""),
        ),
    }


def hash_password(password: str) -> str:
    """Return a salted PBKDF2 password hash using the Python standard library."""
    salt = secrets.token_bytes(16)
    iterations = 600_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(iterations, base64.urlsafe_b64encode(salt).decode(), base64.urlsafe_b64encode(digest).decode())


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt, expected = stored.split("$", 3)
        if scheme != "pbkdf2_sha256": return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.urlsafe_b64decode(salt), int(iterations))
        return hmac.compare_digest(actual, base64.urlsafe_b64decode(expected))
    except (ValueError, TypeError): return False


def _signed_token(email: str, role: str, account_id: int | None = None) -> str:
    if not _secret(): raise HTTPException(status_code=503, detail="Authentication is not configured. Set ADMIN_TOKEN_SECRET.")
    payload = {"sub": email, "role": role, "exp": int(time.time()) + 28800}
    if account_id is not None: payload["account_id"] = account_id
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def issue_token(email: str, password: str) -> tuple[str, str]:
    """Issue a temporary environment-configured demo account token."""
    credentials = _credentials()
    if not _secret() or any(not user_email or not user_password for user_email, user_password in credentials.values()):
        raise HTTPException(status_code=503, detail="Authentication is not configured. Set the admin and staff credentials and token secret.")
    role = next((candidate_role for candidate_role, (candidate_email, candidate_password) in credentials.items() if hmac.compare_digest(email, candidate_email) and hmac.compare_digest(password, candidate_password)), None)
    if role is None: raise HTTPException(status_code=401, detail="Incorrect email or password")
    return _signed_token(email, role), role


def issue_account_token(email: str, role: str, account_id: int) -> str:
    return _signed_token(email, role, account_id)


def verify_token(token: str) -> dict[str, str | int]:
    try:
        if not _secret(): raise ValueError
        body, signature = token.split(".", 1)
        expected = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if not hmac.compare_digest(signature, expected) or payload["exp"] < time.time() or payload["role"] not in {"admin", "staff"}: raise ValueError
        return payload
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Your session is invalid or expired") from None
