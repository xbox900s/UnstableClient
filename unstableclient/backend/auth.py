from __future__ import annotations

import base64
import os
from datetime import datetime
from typing import Any, Dict

import bcrypt

from . import db


ROLE_ORDER = [
    "OWNER",
    "MANAGER",
    "ADMIN",
    "CREATOR_PRO",
    "CREATOR_PLUS",
    "CREATOR",
    "PRO",
    "PLUS",
    "USER",
]


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_session(user_id: int) -> str:
    token = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8").rstrip("=")
    now = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO sessions (user_id, token, created_at, last_seen) VALUES (?, ?, ?, ?)",
        (user_id, token, now, now),
    )
    return token


def touch_session(token: str) -> None:
    now = datetime.utcnow().isoformat()
    db.execute("UPDATE sessions SET last_seen = ? WHERE token = ?", (now, token))


def get_user_by_session(token: str) -> Dict[str, Any] | None:
    row = db.fetch_one(
        "SELECT users.* FROM sessions JOIN users ON users.id = sessions.user_id WHERE sessions.token = ?",
        (token,),
    )
    return row


def register_user(email: str, username: str, password: str) -> Dict[str, Any]:
    existing = db.fetch_one("SELECT id FROM users LIMIT 1")
    role = "ADMIN" if not existing else "USER"
    now = datetime.utcnow().isoformat()
    pass_hash = hash_password(password)
    user_id = db.execute(
        "INSERT INTO users (email, username, pass_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
        (email, username, pass_hash, role, now),
    )
    return db.fetch_one(
        "SELECT id, email, username, role, created_at, is_active, profile_description FROM users WHERE id = ?",
        (user_id,),
    )


def authenticate(identifier: str, password: str) -> Dict[str, Any] | None:
    row = db.fetch_one(
        "SELECT * FROM users WHERE email = ? OR username = ?",
        (identifier, identifier),
    )
    if not row:
        return None
    if not row["is_active"]:
        return None
    if not verify_password(password, row["pass_hash"]):
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "username": row["username"],
        "role": row["role"],
        "profile_description": row["profile_description"],
        "created_at": row["created_at"],
    }
