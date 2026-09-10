import base64
import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from html import escape

import httpx
from fastapi import HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import settings
from .models import LoginAttempt, User, UserSession, VerificationCode

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_RE = re.compile(r"^\+[1-9]\d{7,14}$")
PBKDF2_ITERATIONS = 600_000


def normalize_email(value: str | None) -> str | None:
    cleaned = (value or "").strip().lower()
    if not cleaned:
        return None
    if not EMAIL_RE.match(cleaned):
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    return cleaned


def normalize_phone(value: str | None) -> str | None:
    cleaned = re.sub(r"[\s()-]", "", value or "")
    if not cleaned:
        return None
    if not PHONE_RE.match(cleaned):
        raise HTTPException(status_code=400, detail="Use international format, for example +919876543210")
    return cleaned


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode().rstrip("="),
        base64.urlsafe_b64encode(digest).decode().rstrip("="),
    )


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, iterations, salt_text, expected_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text + "==")
        expected = base64.urlsafe_b64decode(expected_text + "==")
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False


def find_user(db: Session, identifier: str) -> User | None:
    value = identifier.strip().lower()
    if "@" in value:
        return db.scalar(select(User).where(User.email == value))
    phone = normalize_phone(value)
    return db.scalar(select(User).where(User.phone == phone))


def _identifier_hash(identifier: str) -> str:
    return hashlib.sha256(identifier.strip().lower().encode()).hexdigest()


def enforce_login_limit(db: Session, identifier: str) -> None:
    item = db.scalar(select(LoginAttempt).where(LoginAttempt.identifier_hash == _identifier_hash(identifier)))
    if item and item.locked_until and item.locked_until > datetime.utcnow():
        raise HTTPException(status_code=429, detail="Too many sign-in attempts. Try again in 15 minutes.")


def record_login_failure(db: Session, identifier: str) -> None:
    now = datetime.utcnow()
    digest = _identifier_hash(identifier)
    item = db.scalar(select(LoginAttempt).where(LoginAttempt.identifier_hash == digest))
    if not item or item.window_started_at < now - timedelta(minutes=15):
        if item:
            db.delete(item)
        item = LoginAttempt(identifier_hash=digest, failures=0, window_started_at=now)
        db.add(item)
    item.failures += 1
    if item.failures >= 5:
        item.locked_until = now + timedelta(minutes=15)
    db.commit()


def clear_login_failures(db: Session, identifier: str) -> None:
    item = db.scalar(select(LoginAttempt).where(LoginAttempt.identifier_hash == _identifier_hash(identifier)))
    if item:
        db.delete(item)
        db.commit()


def public_user(user: User) -> dict:
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "email_verified": user.email_verified,
        "phone_verified": user.phone_verified,
        "role": user.role,
        "must_change_password": user.must_change_password,
    }


def session_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user: User, request: Request, response: Response) -> dict:
    token = secrets.token_urlsafe(48)
    now = datetime.utcnow()
    expires = now + timedelta(days=settings.auth_session_days)
    db.add(UserSession(
        user_id=user.id,
        token_hash=session_token_hash(token),
        expires_at=expires,
        user_agent=(request.headers.get("user-agent") or "")[:255],
    ))
    user.last_login_at = now
    db.commit()
    response.set_cookie(
        settings.auth_cookie_name,
        token,
        max_age=settings.auth_session_days * 86400,
        expires=expires.replace(tzinfo=timezone.utc),
        httponly=True,
        secure=settings.public_app_url.startswith("https://"),
        samesite="lax",
        path="/",
    )
    return {"user": public_user(user), "expires_at": expires.isoformat() + "Z"}


def authenticated_user(db: Session, request: Request) -> User | None:
    token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        return None
    now = datetime.utcnow()
    session = db.scalar(select(UserSession).where(
        UserSession.token_hash == session_token_hash(token),
        UserSession.expires_at > now,
    ))
    if not session:
        return None
    user = db.get(User, session.user_id)
    if not user or not user.active:
        return None
    session.last_seen_at = now
    db.commit()
    return user


def revoke_session(db: Session, request: Request, response: Response) -> None:
    token = request.cookies.get(settings.auth_cookie_name)
    if token:
        session = db.scalar(select(UserSession).where(UserSession.token_hash == session_token_hash(token)))
        if session:
            db.delete(session)
            db.commit()
    response.delete_cookie(settings.auth_cookie_name, path="/", samesite="lax")


def _code_hash(destination: str, purpose: str, code: str) -> str:
    pepper = settings.auth_code_pepper or "local-development-only"
    return hmac.new(pepper.encode(), f"{destination}|{purpose}|{code}".encode(), hashlib.sha256).hexdigest()


def issue_email_code(db: Session, email: str, purpose: str = "login") -> None:
    user = db.scalar(select(User).where(User.email == email, User.active.is_(True)))
    # Keep the API response identical for unknown accounts.
    if (purpose == "login" and not user) or (purpose == "register" and user):
        return
    now = datetime.utcnow()
    recent = db.scalar(select(func.count(VerificationCode.id)).where(
        VerificationCode.destination == email,
        VerificationCode.created_at > now - timedelta(minutes=15),
    )) or 0
    if recent >= 3:
        raise HTTPException(status_code=429, detail="Too many codes requested. Try again in 15 minutes.")
    if not settings.resend_api_key:
        raise HTTPException(status_code=503, detail="Email code sign-in is not configured yet")
    if not settings.auth_code_pepper:
        raise HTTPException(status_code=503, detail="Secure email code sign-in is not configured yet")
    code = f"{secrets.randbelow(1_000_000):06d}"
    record = VerificationCode(
        user_id=user.id if user else None,
        destination=email,
        purpose=purpose,
        code_hash=_code_hash(email, purpose, code),
        expires_at=now + timedelta(minutes=settings.auth_code_minutes),
    )
    db.add(record)
    db.flush()
    html = f"""<div style='font-family:Arial,sans-serif;max-width:520px;margin:auto;padding:28px'>
      <h1 style='color:#155f4b'>Your NiveshDesk code</h1>
      <p>Use this code to securely open your financial workspace:</p>
      <div style='font-size:34px;letter-spacing:8px;font-weight:700;padding:20px;background:#f2f6f2;border-radius:12px'>{escape(code)}</div>
      <p>This code expires in {settings.auth_code_minutes} minutes. If you did not request it, ignore this email.</p>
    </div>"""
    response = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        json={"from": settings.resend_from, "to": [email], "subject": f"{code} is your NiveshDesk code", "html": html},
        timeout=20,
    )
    if response.status_code >= 300:
        db.rollback()
        raise HTTPException(status_code=502, detail="The sign-in code could not be sent")
    db.commit()


def consume_email_code(db: Session, email: str, code: str, purpose: str = "login") -> User | None:
    now = datetime.utcnow()
    record = db.scalar(select(VerificationCode).where(
        VerificationCode.destination == email,
        VerificationCode.purpose == purpose,
        VerificationCode.consumed_at.is_(None),
        VerificationCode.expires_at > now,
    ).order_by(VerificationCode.created_at.desc()))
    if not record or record.attempts >= 5:
        raise HTTPException(status_code=400, detail="Code is invalid or expired")
    record.attempts += 1
    if not hmac.compare_digest(record.code_hash, _code_hash(email, purpose, code)):
        db.commit()
        raise HTTPException(status_code=400, detail="Code is invalid or expired")
    record.consumed_at = now
    user = db.get(User, record.user_id) if record.user_id else None
    if purpose == "login":
        if not user or not user.active:
            raise HTTPException(status_code=400, detail="Account is unavailable")
        user.email_verified = True
    db.commit()
    return user
