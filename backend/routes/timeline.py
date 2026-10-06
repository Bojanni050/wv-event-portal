import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import db, get_child_for, get_current_user, get_event_for, is_staff, now, touch_event
from models import TimelineItem

router = APIRouter(tags=["timeline"])
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class TimelineIn(BaseModel):
    time: str
    title: str
    description: Optional[str] = None
    icon: str = "sparkles"
    status: Optional[str] = None


class TimelineUpdate(BaseModel):
    time: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    status: Optional[str] = None


def sort_key(item: dict):
    return (item["time"] < "06:00", item["time"])


def _check(fields: dict, staff: bool):
    if "time" in fields and not TIME_RE.match(fields["time"] or ""):
        raise HTTPException(400, "Gebruik een tijd als 20:30")
    if "status" in fields:
        if not staff:
            raise HTTPException(403, "Alleen White Vision kan onderdelen bevestigen")
        if fields["status"] not in {"suggested", "confirmed"}:
            raise HTTPException(400, "Ongeldige status")


@router.get("/events/{event_id}/timeline")
async def list_timeline(event_id: str, user: dict = Depends(get_current_user)):
    await get_event_for(user, event_id)
    docs = await db.timeline_items.find({"event_id": event_id}).to_list(500)
    docs.sort(key=sort_key)
    return [TimelineItem.from_mongo(d).out() for d in docs]


@router.post("/events/{event_id}/timeline")
async def add_timeline(event_id: str, body: TimelineIn, user: dict = Depends(get_current_user)):
    await get_event_for(user, event_id)
    staff = is_staff(user)
    fields = body.model_dump(exclude_none=True)
    _check(fields, staff)
    fields["status"] = fields.get("status") or ("confirmed" if staff else "suggested")
    item = TimelineItem(event_id=event_id, **fields, created_by_role=user["role"], created_at=now())
    res = await db.timeline_items.insert_one(item.to_mongo())
    item.id = str(res.inserted_id)
    await touch_event(event_id)
    return item.out()


@router.patch("/timeline/{item_id}")
async def update_timeline(item_id: str, body: TimelineUpdate, user: dict = Depends(get_current_user)):
    doc = await get_child_for(user, "timeline_items", item_id)
    staff = is_staff(user)
    if not staff and doc["status"] != "suggested":
        raise HTTPException(403, "Definitieve onderdelen kunnen alleen door White Vision worden gewijzigd")
    fields = body.model_dump(exclude_unset=True)
    _check(fields, staff)
    await db.timeline_items.update_one({"_id": doc["_id"]}, {"$set": fields})
    await touch_event(doc["event_id"])
    return TimelineItem.from_mongo({**doc, **fields}).out()


@router.delete("/timeline/{item_id}")
async def delete_timeline(item_id: str, user: dict = Depends(get_current_user)):
    doc = await get_child_for(user, "timeline_items", item_id)
    if not is_staff(user) and doc["status"] != "suggested":
        raise HTTPException(403, "Definitieve onderdelen kunnen alleen door White Vision worden verwijderd")
    await db.timeline_items.delete_one({"_id": doc["_id"]})
    await touch_event(doc["event_id"])
    return {"ok": True}
