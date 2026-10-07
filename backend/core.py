"""Shared foundation: auth (JWT cookie sessions), role checks and event scoping.

PostgreSQL / SQLAlchemy port of the old Motor ``core``. ``get_current_user``
returns a plain dict whose ``id`` / ``customer_id`` / ``dj_id`` are ``UUID``
objects (FastAPI serializes them to strings when they reach JSON).
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import and_, false, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import Event, Message, User

JWT_ALGORITHM = "HS256"
ACCESS_TTL = timedelta(minutes=15)
REFRESH_TTL = timedelta(days=7)

# Role registry: extend here to add roles later.
STAFF_ROLES = {"admin", "dj"}
ALL_ROLES = STAFF_ROLES | {"customer"}


def now() -> datetime:
    return datetime.now(timezone.utc)


def to_uuid(value) -> uuid.UUID:
    """Parse an id from the URL, mirroring the old ``oid()`` 404 behaviour."""
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(404, "Niet gevonden")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _secret() -> str:
    return os.environ["JWT_SECRET"]


def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "exp": now() + ACCESS_TTL, "type": "access"}
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": now() + REFRESH_TTL, "type": "refresh"}
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str, token_type: str) -> dict:
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Sessie verlopen")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Ongeldige sessie")
    if payload.get("type") != token_type:
        raise HTTPException(401, "Ongeldige sessie")
    return payload


def set_access_cookie(response: Response, user_id: str, email: str):
    response.set_cookie("access_token", create_access_token(user_id, email), httponly=True, secure=True,
                        samesite="none", max_age=int(ACCESS_TTL.total_seconds()), path="/")


def set_auth_cookies(response: Response, user_id: str, email: str):
    set_access_cookie(response, user_id, email)
    response.set_cookie("refresh_token", create_refresh_token(user_id), httponly=True, secure=True,
                        samesite="none", max_age=int(REFRESH_TTL.total_seconds()), path="/")


def clear_auth_cookies(response: Response):
    response.delete_cookie("access_token", path="/", secure=True, samesite="none")
    response.delete_cookie("refresh_token", path="/", secure=True, samesite="none")


def user_dict(user: User) -> dict:
    """Serialize a User row to the dict shape routes have always used."""
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "customer_id": user.customer_id,
        "dj_id": user.dj_id,
        "created_at": user.created_at,
    }


async def get_current_user(request: Request, session: AsyncSession = Depends(get_session)) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            token = header[7:]
    if not token:
        raise HTTPException(401, "Niet ingelogd")
    payload = decode_token(token, "access")
    user = await session.get(User, to_uuid(payload["sub"]))
    if not user:
        raise HTTPException(401, "Gebruiker niet gevonden")
    return user_dict(user)


def is_staff(user: dict) -> bool:
    return user["role"] in STAFF_ROLES


async def require_staff(user: dict = Depends(get_current_user)) -> dict:
    if not is_staff(user):
        raise HTTPException(403, "Alleen voor White Vision")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "Alleen voor beheerders")
    return user


def event_scope(user: dict):
    """SQLAlchemy condition limiting events to what ``user`` may see (None = all)."""
    if user["role"] == "admin":
        return None
    if user["role"] == "dj":
        return Event.dj_id == user["dj_id"] if user.get("dj_id") else false()
    return Event.customer_id == user["customer_id"] if user.get("customer_id") else false()


async def get_event_for(session: AsyncSession, user: dict, event_id) -> Event:
    stmt = select(Event).where(Event.id == to_uuid(event_id))
    scope = event_scope(user)
    if scope is not None:
        stmt = stmt.where(scope)
    ev = await session.scalar(stmt)
    if not ev:
        raise HTTPException(404, "Event niet gevonden")
    return ev


async def get_child_for(session: AsyncSession, model, user: dict, item_id):
    """Load a child row and enforce that the user may access its event."""
    doc = await session.get(model, to_uuid(item_id))
    if not doc:
        raise HTTPException(404, "Niet gevonden")
    await get_event_for(session, user, doc.event_id)
    return doc


def unread_filter(user: dict):
    if is_staff(user):
        return and_(Message.sender_role == "customer", Message.read_by_staff.is_(False))
    return and_(Message.sender_role.in_(list(STAFF_ROLES)), Message.read_by_customer.is_(False))


async def touch_event(session: AsyncSession, event_id):
    ev = await session.get(Event, to_uuid(event_id))
    if ev:
        ev.updated_at = now()
