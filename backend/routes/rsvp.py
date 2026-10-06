from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import db, get_child_for, get_current_user, get_event_for, now, touch_event
from models import Rsvp

router = APIRouter(tags=["rsvp"])
MAX_PER_EVENT = 1000


class RsvpIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: Optional[str] = Field(default=None, max_length=200)
    attending: str
    guests: int = Field(default=1, ge=1, le=20)
    dietary: Optional[str] = Field(default=None, max_length=300)
    message: Optional[str] = Field(default=None, max_length=1000)


@router.post("/public/invitations/{token}/rsvp")
async def submit_rsvp(token: str, body: RsvpIn):
    inv = await db.invitations.find_one({"share_token": token})
    if not inv:
        raise HTTPException(404, "Uitnodiging niet gevonden")
    if not inv.get("rsvp_enabled", True):
        raise HTTPException(400, "Aanmelden is gesloten")
    if body.attending not in {"yes", "no", "maybe"}:
        raise HTTPException(400, "Kies of je komt")
    if not body.name.strip():
        raise HTTPException(400, "Vul je naam in")
    if await db.rsvps.count_documents({"event_id": inv["event_id"]}) >= MAX_PER_EVENT:
        raise HTTPException(400, "Maximum aantal reacties bereikt")
    fields = body.model_dump()
    fields["name"] = fields["name"].strip()
    if fields["attending"] == "no":
        fields["guests"] = 0
    rsvp = Rsvp(event_id=inv["event_id"], **fields, created_at=now())
    await db.rsvps.insert_one(rsvp.to_mongo())
    await touch_event(inv["event_id"])
    return {"ok": True, "name": rsvp.name, "attending": rsvp.attending}


@router.get("/events/{event_id}/rsvps")
async def list_rsvps(event_id: str, user: dict = Depends(get_current_user)):
    await get_event_for(user, event_id)
    docs = await db.rsvps.find({"event_id": event_id}).sort("created_at", -1).to_list(MAX_PER_EVENT)
    return [Rsvp.from_mongo(d).out() for d in docs]


@router.delete("/rsvps/{rsvp_id}")
async def delete_rsvp(rsvp_id: str, user: dict = Depends(get_current_user)):
    doc = await get_child_for(user, "rsvps", rsvp_id)
    await db.rsvps.delete_one({"_id": doc["_id"]})
    return {"ok": True}
