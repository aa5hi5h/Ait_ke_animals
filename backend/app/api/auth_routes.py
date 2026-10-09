"""Reviewer sign up, sign in, and profile. Accounts live in SQLite."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.db import get_connection
from app.security import hash_password, new_token, utc_now, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")


class Credentials(BaseModel):
    email: str
    password: str = Field(min_length=1)


class ProfileUpdate(BaseModel):
    name: str
    dob: str


def _normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def _validate_credentials(email: str, password: str) -> str:
    normalized = _normalize_email(email)
    if not EMAIL_PATTERN.match(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enter a valid official email address, for example reviewer@department.gov.in.",
        )
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long.",
        )
    return normalized


def _user_payload(row, token: str | None = None) -> dict:
    name = row["name"] or ""
    body = {
        "email": row["email"],
        "name": name,
        "dob": row["dob"] or "",
        "needsProfile": not bool(name.strip()),
    }
    if token:
        body["token"] = token
    return body


def get_current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in required.",
        )
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in required.",
        )
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT users.email, users.name, users.dob
            FROM sessions
            JOIN users ON users.email = sessions.email
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please sign in again.",
        )
    return {"email": row["email"], "name": row["name"], "dob": row["dob"], "token": token}


def _issue_session(connection, email: str) -> str:
    token = new_token()
    connection.execute(
        "INSERT INTO sessions (token, email, created_at) VALUES (?, ?, ?)",
        (token, email, utc_now()),
    )
    return token


@router.post("/signup")
def signup(body: Credentials) -> dict:
    email = _validate_credentials(body.email, body.password)
    with get_connection() as connection:
        existing = connection.execute(
            "SELECT email FROM users WHERE email = ?", (email,)
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account already exists for this email. Sign in instead.",
            )
        connection.execute(
            """
            INSERT INTO users (email, password_hash, name, dob, created_at)
            VALUES (?, ?, '', '', ?)
            """,
            (email, hash_password(body.password), utc_now()),
        )
        token = _issue_session(connection, email)
        row = connection.execute(
            "SELECT email, name, dob FROM users WHERE email = ?", (email,)
        ).fetchone()
    payload = _user_payload(row, token)
    payload["needsProfile"] = True
    return payload


@router.post("/signin")
def signin(body: Credentials) -> dict:
    email = _validate_credentials(body.email, body.password)
    with get_connection() as connection:
        row = connection.execute(
            "SELECT email, password_hash, name, dob FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No account for this email. Please sign up first.",
            )
        if not verify_password(body.password, row["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
            )
        token = _issue_session(connection, email)
    return _user_payload(row, token)


@router.post("/profile")
def save_profile(body: ProfileUpdate, user: dict = Depends(get_current_user)) -> dict:
    clean_name = " ".join(str(body.name or "").split())
    clean_dob = str(body.dob or "").strip()
    if len(clean_name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Enter your full name."
        )
    if not clean_dob:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enter your date of birth.",
        )
    with get_connection() as connection:
        connection.execute(
            "UPDATE users SET name = ?, dob = ? WHERE email = ?",
            (clean_name, clean_dob, user["email"]),
        )
        row = connection.execute(
            "SELECT email, name, dob FROM users WHERE email = ?",
            (user["email"],),
        ).fetchone()
    return _user_payload(row, user["token"])


@router.post("/logout")
def logout(user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as connection:
        connection.execute("DELETE FROM sessions WHERE token = ?", (user["token"],))
    return {"ok": True}
