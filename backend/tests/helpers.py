"""Shared test helpers: base URL, credentials, login and Postgres access.

The suites talk to a running backend over HTTP and, where they need to inspect
or seed rows directly, use the SQLAlchemy session instead of the old Mongo
client.
"""
import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from sqlalchemy import delete, func, select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from models import Customer, LoginAttempt, PasswordResetToken, User  # noqa: E402

# These helpers are called from sync tests via asyncio.run() (a fresh loop per
# call), so use NullPool: pooled asyncpg connections must not outlive their loop.
_engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
_Session = async_sessionmaker(_engine, expire_on_commit=False)

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://127.0.0.1:8001").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = (os.environ.get("ADMIN_EMAIL", "admin@white-vision.nl"), os.environ.get("ADMIN_PASSWORD", "admin12345"))
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "demo12345")
DJ_BAS = ("bas@white-vision.nl", DEMO_PASSWORD)
DJ_THOMAS = ("thomas@white-vision.nl", DEMO_PASSWORD)
CUST_JEROEN = ("jeroen@example.nl", DEMO_PASSWORD)
CUST_SANNE = ("sanne@example.nl", DEMO_PASSWORD)
WP_API_KEY = os.environ.get("WP_API_KEY", "dev-wp-key")
SANDBOX_EMAIL = "delivered@resend.dev"


def httponly_over_http(session: requests.Session) -> requests.Session:
    """Secure cookies are not sent over plain http; mirror tokens into headers."""
    access = session.cookies.get("access_token")
    refresh = session.cookies.get("refresh_token")
    if access:
        session.headers["Authorization"] = f"Bearer {access}"
    if refresh:
        session.headers["Cookie"] = f"refresh_token={refresh}"
    return session


def login(email: str, password: str):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return httponly_over_http(s), r.json()


def _run(coro):
    return asyncio.run(coro)


def _now():
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- users
async def _get_user(email):
    async with _Session() as s:
        u = await s.scalar(select(User).where(User.email == email.lower()))
        if not u:
            return None
        return {"id": str(u.id), "role": u.role,
                "customer_id": str(u.customer_id) if u.customer_id else None,
                "dj_id": str(u.dj_id) if u.dj_id else None}


def get_user(email):
    return _run(_get_user(email))


def delete_user(email):
    async def go():
        async with _Session() as s:
            u = await s.scalar(select(User).where(User.email == email.lower()))
            if u:
                await s.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == u.id))
                await s.delete(u)
                await s.commit()
    _run(go())


# --------------------------------------------------------------------------- customers
def count_customers(email):
    async def go():
        async with _Session() as s:
            return await s.scalar(select(func.count()).select_from(Customer)
                                  .where(Customer.email == email.lower()))
    return _run(go())


def delete_customer(email):
    async def go():
        async with _Session() as s:
            await s.execute(Customer.__table__.delete().where(Customer.email == email.lower()))
            await s.commit()
    _run(go())


def delete_customer_by_id(customer_id):
    async def go():
        async with _Session() as s:
            await s.execute(Customer.__table__.delete().where(Customer.id == uuid.UUID(str(customer_id))))
            await s.commit()
    _run(go())


# --------------------------------------------------------------------------- reset tokens
def add_reset_token(user_id, token_hash, purpose="reset", created_at=None, expires_at=None, used=False):
    created_at = created_at or _now()
    expires_at = expires_at or (created_at + timedelta(hours=1))

    async def go():
        async with _Session() as s:
            s.add(PasswordResetToken(user_id=uuid.UUID(str(user_id)), token_hash=token_hash, used=used,
                                     purpose=purpose, created_at=created_at, expires_at=expires_at))
            await s.commit()
    _run(go())


def count_reset_tokens(user_id=None, purpose=None):
    async def go():
        async with _Session() as s:
            stmt = select(func.count()).select_from(PasswordResetToken)
            if user_id is not None:
                stmt = stmt.where(PasswordResetToken.user_id == uuid.UUID(str(user_id)))
            if purpose is not None:
                stmt = stmt.where(PasswordResetToken.purpose == purpose)
            return await s.scalar(stmt)
    return _run(go())


def list_reset_tokens(user_id):
    async def go():
        async with _Session() as s:
            rows = (await s.scalars(select(PasswordResetToken)
                                    .where(PasswordResetToken.user_id == uuid.UUID(str(user_id)))
                                    .order_by(PasswordResetToken.created_at.asc()))).all()
            return [{"used": r.used, "purpose": r.purpose, "token_hash": r.token_hash,
                     "created_at": r.created_at, "expires_at": r.expires_at} for r in rows]
    return _run(go())


def get_reset_token(user_id, purpose=None):
    async def go():
        async with _Session() as s:
            stmt = select(PasswordResetToken).where(PasswordResetToken.user_id == uuid.UUID(str(user_id)))
            if purpose is not None:
                stmt = stmt.where(PasswordResetToken.purpose == purpose)
            r = await s.scalar(stmt.order_by(PasswordResetToken.created_at.desc()).limit(1))
            return None if not r else {"used": r.used, "purpose": r.purpose, "token_hash": r.token_hash}
    return _run(go())


def get_reset_token_by_hash(token_hash):
    async def go():
        async with _Session() as s:
            r = await s.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
            return None if not r else {"used": r.used}
    return _run(go())


def delete_reset_tokens(user_id=None):
    async def go():
        async with _Session() as s:
            stmt = delete(PasswordResetToken)
            if user_id is not None:
                stmt = stmt.where(PasswordResetToken.user_id == uuid.UUID(str(user_id)))
            await s.execute(stmt)
            await s.commit()
    _run(go())


# --------------------------------------------------------------------------- login attempts
def clear_login_attempts(email=None):
    async def go():
        async with _Session() as s:
            stmt = delete(LoginAttempt)
            if email is not None:
                stmt = stmt.where(LoginAttempt.identifier.endswith(f":{email}", autoescape=True))
            await s.execute(stmt)
            await s.commit()
    _run(go())
