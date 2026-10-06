import os
from datetime import datetime, timezone, timedelta
from typing import Annotated, Optional

import bcrypt
import jwt
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, HTTPException, Request, Response
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

client = AsyncIOMotorClient(os.environ["MONGO_URL"], tz_aware=True)
db = client[os.environ["DB_NAME"]]
fs = AsyncIOMotorGridFSBucket(db, bucket_name="event_files")

JWT_ALGORITHM = "HS256"
ACCESS_TTL = timedelta(minutes=15)
REFRESH_TTL = timedelta(days=7)

# Role registry: extend here to add roles later.
STAFF_ROLES = {"admin", "dj"}
ALL_ROLES = STAFF_ROLES | {"customer"}


def now() -> datetime:
    return datetime.now(timezone.utc)


def oid(value) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(404, "Niet gevonden")


PyObjectId = Annotated[str, BeforeValidator(lambda v: str(v) if isinstance(v, ObjectId) else v)]


class BaseDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    @classmethod
    def from_mongo(cls, doc: dict):
        return cls.model_validate(doc)

    def to_mongo(self) -> dict:
        data = self.model_dump(exclude={"id"})
        if self.id:
            data["_id"] = ObjectId(self.id)
        return data

    def out(self) -> dict:
        return self.model_dump()


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


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            token = header[7:]
    if not token:
        raise HTTPException(401, "Niet ingelogd")
    payload = decode_token(token, "access")
    user = await db.users.find_one({"_id": oid(payload["sub"])})
    if not user:
        raise HTTPException(401, "Gebruiker niet gevonden")
    from models import User
    return User.from_mongo(user).out()


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


def event_scope(user: dict) -> dict:
    if user["role"] == "admin":
        return {}
    if user["role"] == "dj":
        return {"dj_id": user.get("dj_id") or "__none__"}
    return {"customer_id": user.get("customer_id") or "__none__"}


async def get_event_for(user: dict, event_id: str) -> dict:
    ev = await db.events.find_one({"_id": oid(event_id), **event_scope(user)})
    if not ev:
        raise HTTPException(404, "Event niet gevonden")
    return dict(ev)


async def get_child_for(user: dict, collection: str, item_id: str) -> dict:
    doc = await db[collection].find_one({"_id": oid(item_id)})
    if not doc:
        raise HTTPException(404, "Niet gevonden")
    await get_event_for(user, doc["event_id"])
    return dict(doc)


def unread_filter(user: dict) -> dict:
    if is_staff(user):
        return {"sender_role": "customer", "read_by_staff": False}
    return {"sender_role": {"$in": list(STAFF_ROLES)}, "read_by_customer": False}


async def touch_event(event_id: str):
    await db.events.update_one({"_id": oid(event_id)}, {"$set": {"updated_at": now()}})
