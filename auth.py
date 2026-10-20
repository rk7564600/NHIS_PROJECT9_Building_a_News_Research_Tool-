"""
auth.py
-------
Minimal login for the Streamlit app (Task 7.1).

Configure in .env:
    AUTH_USERNAME=analyst
    AUTH_PASSWORD=choose-a-strong-password          # plain text, OR
    AUTH_PASSWORD_SHA256=<sha256 hex of the password>  # preferred (not stored in clear)
    AUTH_DISABLED=true                              # only for local experiments

Comparison is constant-time. This is meant for a small private deployment; for a
public production app put the tool behind a proper identity provider.
"""

from __future__ import annotations

import hashlib
import hmac
import os

from dotenv import load_dotenv

load_dotenv()


def auth_enabled() -> bool:
    return os.getenv("AUTH_DISABLED", "false").strip().lower() != "true"


def get_username() -> str:
    return os.getenv("AUTH_USERNAME", "analyst")


def is_configured() -> bool:
    """True if a password (plain or hashed) has been set."""
    return bool(os.getenv("AUTH_PASSWORD") or os.getenv("AUTH_PASSWORD_SHA256"))


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_login(username: str, password: str) -> bool:
    if not is_configured():
        return False
    user_ok = hmac.compare_digest(username.strip().encode(), get_username().encode())

    hashed = os.getenv("AUTH_PASSWORD_SHA256")
    if hashed:
        pass_ok = hmac.compare_digest(hash_password(password), hashed.strip().lower())
    else:
        pass_ok = hmac.compare_digest(password.encode(), os.getenv("AUTH_PASSWORD", "").encode())
    return user_ok and pass_ok
