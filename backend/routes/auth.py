import hashlib
import logging
import os
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import (clear_auth_cookies, decode_token, get_current_user, hash_password, now, set_access_cookie,
                  set_auth_cookies, to_uuid, verify_password)
from database import get_session
from mailer import reset_email_html, send_email
from models import LoginAttempt, PasswordResetToken, User
from schemas import ForgotIn, LoginIn, PasswordIn, ResetIn, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger(__name__)
RESET_TTL = timedelta(hours=1)
WELCOME_TTL = timedelta(days=7)
RESET_LIMIT_PER_HOUR = 3


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def issue_password_link(session: AsyncSession, user_id, ttl: timedelta, purpose: str = "reset") -> str:
    token = secrets.token_urlsafe(32)
    session.add(PasswordResetToken(user_id=to_uuid(user_id), token_hash=_hash_token(token), used=False,
                                   purpose=purpose, created_at=now(), expires_at=now() + ttl))
    await session.commit()
    suffix = "&welkom=1" if purpose == "welcome" else ""
    return f"{os.environ['FRONTEND_URL'].rstrip('/')}/wachtwoord-herstellen?token={token}{suffix}"


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/login")
async def login(body: LoginIn, request: Request, response: Response, session: AsyncSession = Depends(get_session)):
    email = body.email.strip().lower()
    ident = f"{client_ip(request)}:{email}"
    attempt = await session.scalar(select(LoginAttempt).where(LoginAttempt.identifier == ident))
    if attempt and attempt.count >= 5:
        if attempt.locked_until and attempt.locked_until > now():
            raise HTTPException(429, "Te veel mislukte pogingen. Probeer het over 15 minuten opnieuw.")
        await session.delete(attempt)
        await session.flush()
        attempt = None

    user = await session.scalar(select(User).where(User.email == email))
    if not user or not verify_password(body.password, user.password_hash):
        if attempt is None:
            attempt = LoginAttempt(identifier=ident, count=1)
            session.add(attempt)
        else:
            attempt.count += 1
        if attempt.count == 5:
            attempt.locked_until = now() + timedelta(minutes=15)
        await session.commit()
        raise HTTPException(401, "Onjuist e-mailadres of wachtwoord")

    if attempt:
        await session.delete(attempt)
        await session.commit()
    set_auth_cookies(response, str(user.id), user.email)
    return UserOut.model_validate(user)


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@router.post("/refresh")
async def refresh(request: Request, response: Response, session: AsyncSession = Depends(get_session)):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "Niet ingelogd")
    payload = decode_token(token, "refresh")
    user = await session.get(User, to_uuid(payload["sub"]))
    if not user:
        raise HTTPException(401, "Gebruiker niet gevonden")
    set_access_cookie(response, str(user.id), user.email)
    return {"ok": True}


@router.post("/password")
async def change_password(body: PasswordIn, user: dict = Depends(get_current_user),
                          session: AsyncSession = Depends(get_session)):
    doc = await session.get(User, user["id"])
    if not verify_password(body.current_password, doc.password_hash):
        raise HTTPException(400, "Huidig wachtwoord klopt niet")
    if len(body.new_password) < 8:
        raise HTTPException(400, "Nieuw wachtwoord moet minimaal 8 tekens hebben")
    doc.password_hash = hash_password(body.new_password)
    await session.commit()
    return {"ok": True}


GENERIC_FORGOT = {"ok": True, "message": "Als dit e-mailadres bij ons bekend is, ontvang je binnen enkele minuten een e-mail."}


@router.post("/forgot-password")
async def forgot_password(body: ForgotIn, session: AsyncSession = Depends(get_session)):
    email = body.email.strip().lower()
    user = await session.scalar(select(User).where(User.email == email))
    if not user:
        return GENERIC_FORGOT
    recent = await session.scalar(select(func.count()).select_from(PasswordResetToken)
                                  .where(PasswordResetToken.user_id == user.id,
                                         PasswordResetToken.created_at > now() - timedelta(hours=1)))
    if recent >= RESET_LIMIT_PER_HOUR:
        return GENERIC_FORGOT
    link = await issue_password_link(session, user.id, RESET_TTL)
    try:
        await send_email(to=email, subject="Stel een nieuw wachtwoord in voor White Vision",
                         html=reset_email_html(user.name, link))
    except Exception as e:  # noqa: BLE001
        log.error("Reset email failed for user %s: %s", user.id, e)
    return GENERIC_FORGOT


@router.post("/reset-password")
async def reset_password(body: ResetIn, session: AsyncSession = Depends(get_session)):
    if len(body.new_password) < 8:
        raise HTTPException(400, "Nieuw wachtwoord moet minimaal 8 tekens hebben")
    doc = await session.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == _hash_token(body.token)))
    if not doc or doc.used or doc.expires_at < now():
        raise HTTPException(400, "Deze link is ongeldig of verlopen. Vraag een nieuwe aan.")
    user = await session.get(User, doc.user_id)
    if not user:
        raise HTTPException(400, "Deze link is ongeldig of verlopen. Vraag een nieuwe aan.")
    user.password_hash = hash_password(body.new_password)
    await session.execute(
        PasswordResetToken.__table__.update().where(PasswordResetToken.user_id == doc.user_id).values(used=True))
    await session.execute(
        LoginAttempt.__table__.delete().where(LoginAttempt.identifier.endswith(f":{user.email}", autoescape=True)))
    await session.commit()
    return {"ok": True}
