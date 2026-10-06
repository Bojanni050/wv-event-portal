import os
import secrets
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from core import db, now
from models import Customer, Event, EventFields

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
async def wordpress_sync(body: WPSyncIn, x_api_key: Optional[str] = Header(default=None)):
    """Upsert a customer (and optionally an event) by WordPress external_id."""
    _check_key(x_api_key)
    c = body.customer
    existing = await db.customers.find_one({"external_id": c.external_id})
    if existing:
        await db.customers.update_one({"_id": existing["_id"]}, {"$set": c.model_dump(exclude_none=True)})
        customer_id = str(existing["_id"])
    else:
        res = await db.customers.insert_one(Customer(**c.model_dump(), created_at=now()).to_mongo())
        customer_id = str(res.inserted_id)

    event_id = None
    if body.event:
        fields = body.event.model_dump(exclude_none=True)
        fields["customer_id"] = customer_id
        ev = await db.events.find_one({"external_id": body.event.external_id})
        if ev:
            await db.events.update_one({"_id": ev["_id"]}, {"$set": {**fields, "updated_at": now()}})
            event_id = str(ev["_id"])
        else:
            fields.setdefault("title", c.name)
            res = await db.events.insert_one(Event(**fields, created_at=now(), updated_at=now()).to_mongo())
            event_id = str(res.inserted_id)
    return {"customer_id": customer_id, "event_id": event_id}
