import hashlib
import logging
import os
import re
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from core import (clear_auth_cookies, db, decode_token, get_current_user, hash_password, now, oid,
                  set_access_cookie, set_auth_cookies, verify_password)
from mailer import reset_email_html, send_email
from models import User

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger(__name__)
RESET_TTL = timedelta(hours=1)
WELCOME_TTL = timedelta(days=7)
RESET_LIMIT_PER_HOUR = 3


class LoginIn(BaseModel):
    email: str
    password: str


class PasswordIn(BaseModel):
    current_password: str
    new_password: str


class ForgotIn(BaseModel):
    email: str = Field(max_length=200)


class ResetIn(BaseModel):
    token: str = Field(max_length=200)
    new_password: str = Field(max_length=200)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def issue_password_link(user_id: str, ttl: timedelta, purpose: str = "reset") -> str:
    token = secrets.token_urlsafe(32)
    await db.password_reset_tokens.insert_one({
        "user_id": user_id, "token_hash": _hash_token(token), "used": False, "purpose": purpose,
        "created_at": now(), "expires_at": now() + ttl})
    suffix = "&welkom=1" if purpose == "welcome" else ""
    return f"{os.environ['FRONTEND_URL'].rstrip('/')}/wachtwoord-herstellen?token={token}{suffix}"


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.strip().lower()
    ident = f"{client_ip(request)}:{email}"
    attempt = await db.login_attempts.find_one({"identifier": ident})
    if attempt and attempt.get("count", 0) >= 5:
        if attempt["locked_until"] > now():
            raise HTTPException(429, "Te veel mislukte pogingen. Probeer het over 15 minuten opnieuw.")
        await db.login_attempts.delete_one({"identifier": ident})
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        updated = await db.login_attempts.find_one_and_update(
            {"identifier": ident}, {"$inc": {"count": 1}}, upsert=True, return_document=True)
        if updated["count"] == 5:
            await db.login_attempts.update_one(
                {"identifier": ident}, {"$set": {"locked_until": now() + timedelta(minutes=15)}})
        raise HTTPException(401, "Onjuist e-mailadres of wachtwoord")
    await db.login_attempts.delete_one({"identifier": ident})
    set_auth_cookies(response, str(user["_id"]), email)
    return User.from_mongo(user).out()


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "Niet ingelogd")
    payload = decode_token(token, "refresh")
    user = await db.users.find_one({"_id": oid(payload["sub"])})
    if not user:
        raise HTTPException(401, "Gebruiker niet gevonden")
    set_access_cookie(response, str(user["_id"]), user["email"])
    return {"ok": True}


@router.post("/password")
async def change_password(body: PasswordIn, user: dict = Depends(get_current_user)):
    doc = await db.users.find_one({"_id": oid(user["id"])})
    if not verify_password(body.current_password, doc["password_hash"]):
        raise HTTPException(400, "Huidig wachtwoord klopt niet")
    if len(body.new_password) < 8:
        raise HTTPException(400, "Nieuw wachtwoord moet minimaal 8 tekens hebben")
    await db.users.update_one({"_id": doc["_id"]}, {"$set": {"password_hash": hash_password(body.new_password)}})
    return {"ok": True}



GENERIC_FORGOT = {"ok": True, "message": "Als dit e-mailadres bij ons bekend is, ontvang je binnen enkele minuten een e-mail."}


@router.post("/forgot-password")
async def forgot_password(body: ForgotIn):
    email = body.email.strip().lower()
    user = await db.users.find_one({"email": email})
    if not user:
        return GENERIC_FORGOT
    recent = await db.password_reset_tokens.count_documents(
        {"user_id": str(user["_id"]), "created_at": {"$gt": now() - timedelta(hours=1)}})
    if recent >= RESET_LIMIT_PER_HOUR:
        return GENERIC_FORGOT
    link = await issue_password_link(str(user["_id"]), RESET_TTL)
    try:
        await send_email(to=email, subject="Stel een nieuw wachtwoord in voor White Vision",
                         html=reset_email_html(user["name"], link))
    except Exception as e:
        log.error("Reset email failed for user %s: %s", user["_id"], e)
    return GENERIC_FORGOT


@router.post("/reset-password")
async def reset_password(body: ResetIn):
    if len(body.new_password) < 8:
        raise HTTPException(400, "Nieuw wachtwoord moet minimaal 8 tekens hebben")
    doc = await db.password_reset_tokens.find_one({"token_hash": _hash_token(body.token)})
    if not doc or doc["used"] or doc["expires_at"] < now():
        raise HTTPException(400, "Deze link is ongeldig of verlopen. Vraag een nieuwe aan.")
    user = await db.users.find_one({"_id": oid(doc["user_id"])})
    if not user:
        raise HTTPException(400, "Deze link is ongeldig of verlopen. Vraag een nieuwe aan.")
    await db.users.update_one({"_id": user["_id"]}, {"$set": {"password_hash": hash_password(body.new_password)}})
    await db.password_reset_tokens.update_many({"user_id": doc["user_id"]}, {"$set": {"used": True}})
    await db.login_attempts.delete_many({"identifier": {"$regex": f":{re.escape(user['email'])}$"}})
    return {"ok": True}
