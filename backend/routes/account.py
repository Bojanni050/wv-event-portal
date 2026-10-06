import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import db, get_current_user, oid

router = APIRouter(prefix="/account", tags=["account"])
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PROFILE_COLLECTION = {"customer": ("customers", "customer_id"), "dj": ("djs", "dj_id")}


class AccountIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=200)
    phone: Optional[str] = Field(default=None, max_length=40)


async def _profile_doc(user: dict):
    target = PROFILE_COLLECTION.get(user["role"])
    if not target or not user.get(target[1]):
        return None, None
    return target[0], await db[target[0]].find_one({"_id": oid(user[target[1]])})


async def _account_out(user: dict) -> dict:
    _, profile = await _profile_doc(user)
    return {**user, "phone": (profile or {}).get("phone")}


@router.get("")
async def get_account(user: dict = Depends(get_current_user)):
    return await _account_out(user)


@router.patch("")
async def update_account(body: AccountIn, user: dict = Depends(get_current_user)):
    email = body.email.strip().lower()
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Vul je naam in")
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Vul een geldig e-mailadres in")
    if email != user["email"] and await db.users.find_one({"email": email}):
        raise HTTPException(400, "Dit e-mailadres is al in gebruik")
    await db.users.update_one({"_id": oid(user["id"])}, {"$set": {"name": name, "email": email}})
    collection, profile = await _profile_doc(user)
    if profile:
        await db[collection].update_one({"_id": profile["_id"]},
                                        {"$set": {"name": name, "email": email, "phone": body.phone or None}})
    return await _account_out({**user, "name": name, "email": email})
