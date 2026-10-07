import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import get_current_user
from database import get_session
from models import Customer, DJ, User

router = APIRouter(prefix="/account", tags=["account"])
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# role -> (ORM model, attribute on the user row holding the profile id)
PROFILE_MODEL = {"customer": (Customer, "customer_id"), "dj": (DJ, "dj_id")}


class AccountIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=200)
    phone: Optional[str] = Field(default=None, max_length=40)


async def _profile(session: AsyncSession, user: dict):
    target = PROFILE_MODEL.get(user["role"])
    if not target:
        return None, None
    model, link = target
    pid = user.get(link)
    if not pid:
        return model, None
    return model, await session.get(model, pid)


async def _account_out(session: AsyncSession, user: dict) -> dict:
    _, profile = await _profile(session, user)
    return {**user, "phone": profile.phone if profile else None}


@router.get("")
async def get_account(user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await _account_out(session, user)


@router.patch("")
async def update_account(body: AccountIn, user: dict = Depends(get_current_user),
                         session: AsyncSession = Depends(get_session)):
    email = body.email.strip().lower()
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Vul je naam in")
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Vul een geldig e-mailadres in")
    if email != user["email"]:
        existing = await session.scalar(select(User).where(User.email == email))
        if existing:
            raise HTTPException(400, "Dit e-mailadres is al in gebruik")
    doc = await session.get(User, user["id"])
    doc.name = name
    doc.email = email
    _, profile = await _profile(session, user)
    if profile:
        profile.name = name
        profile.email = email
        profile.phone = body.phone or None
    await session.commit()
    return await _account_out(session, {**user, "name": name, "email": email})
