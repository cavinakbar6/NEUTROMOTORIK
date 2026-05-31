"""Core security module — JWT auth, password hashing, data sanitization."""

import re
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import bcrypt

from config import JWT_SECRET, JWT_EXPIRE_HOURS, API_KEY, DATA_RETENTION_DAYS

DEFAULT_RETENTION_DAYS = 90


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(hours=JWT_EXPIRE_HOURS)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")


def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_api_key_from_env() -> str:
    return API_KEY


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def generate_session_key() -> str:
    return secrets.token_urlsafe(32)


def sanitize_patient_id(patient_id: str) -> str:
    sanitized = re.sub(r"<[^>]*>", "", patient_id)
    sanitized = re.sub(r"[<>&'\"();]", "", sanitized)
    return sanitized.strip()[:64]