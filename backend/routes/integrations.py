import os
import secrets
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from core import now
from database import get_session
from models import Customer, Event
from schemas import EventFields

router = APIRouter(prefix="/integrations", tags=["integrations"])


class WPCustomer(BaseModel):
    external_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None


class WPEvent(EventFields):
    external_id: str


class WPSyncIn(BaseModel):
    customer: WPCustomer
    event: Optional[WPEvent] = None


def _check_key(key: Optional[str]):
    expected = os.environ.get("WP_API_KEY")
    if not expected or not key or not secrets.compare_digest(key, expected):
        raise HTTPException(401, "Ongeldige API-sleutel")


@router.post("/wordpress/sync")
async def wordpress_sync(body: WPSyncIn, x_api_key: Optional[str] = Header(default=None),
                         session: AsyncSession = Depends(get_session)):
    """Upsert a customer (and optionally an event) by WordPress external_id."""
    _check_key(x_api_key)
    c = body.customer
    existing = await session.scalar(select(Customer).where(Customer.external_id == c.external_id))
    if existing:
        for key, value in c.model_dump(exclude_none=True).items():
            setattr(existing, key, value)
        customer = existing
    else:
        customer = Customer(**c.model_dump(), created_at=now())
        session.add(customer)
    await session.flush()

    event_id = None
    if body.event:
        fields = body.event.model_dump(exclude_none=True)
        fields["customer_id"] = customer.id
        ev = await session.scalar(select(Event).where(Event.external_id == body.event.external_id))
        if ev:
            for key, value in fields.items():
                setattr(ev, key, value)
            ev.updated_at = now()
        else:
            fields.setdefault("title", c.name)
            ev = Event(**fields, created_at=now(), updated_at=now())
            session.add(ev)
        await session.flush()
        event_id = str(ev.id)
    await session.commit()
    return {"customer_id": str(customer.id), "event_id": event_id}
