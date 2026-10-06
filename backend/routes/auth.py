from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from core import (clear_auth_cookies, db, decode_token, get_current_user, hash_password, now, oid,
                  set_access_cookie, set_auth_cookies, verify_password)
from models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    password: str


class PasswordIn(BaseModel):
    current_password: str
    new_password: str


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
        await db.login_attempts.update_one(
            {"identifier": ident},
            {"$inc": {"count": 1}, "$set": {"locked_until": now() + timedelta(minutes=15)}}, upsert=True)
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
