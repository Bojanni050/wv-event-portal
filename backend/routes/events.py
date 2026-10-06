from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from core import db, event_scope, fs, get_current_user, get_event_for, is_staff, now, require_admin
from models import CUSTOMER_EDITABLE, EVENT_STATUSES, Event, EventCreate, EventFields
from services import enrich_event

router = APIRouter(tags=["events"])


def _validate(fields: dict):
    if "status" in fields and fields["status"] not in EVENT_STATUSES:
        raise HTTPException(400, "Ongeldige status")


@router.get("/events")
async def list_events(user: dict = Depends(get_current_user)):
    docs = await db.events.find(event_scope(user)).to_list(1000)
    docs.sort(key=lambda e: e.get("date") or "9999")
    return [await enrich_event(d, user) for d in docs]


@router.post("/events")
async def create_event(body: EventCreate, user: dict = Depends(require_admin)):
    fields = body.model_dump(exclude_none=True)
    _validate(fields)
    event = Event(**fields, created_at=now(), updated_at=now())
    res = await db.events.insert_one(event.to_mongo())
    return await enrich_event(await db.events.find_one({"_id": res.inserted_id}), user)


@router.get("/events/{event_id}")
async def get_event(event_id: str, user: dict = Depends(get_current_user)):
    return await enrich_event(await get_event_for(user, event_id), user)


@router.patch("/events/{event_id}")
async def update_event(event_id: str, body: EventFields, user: dict = Depends(get_current_user)):
    ev = await get_event_for(user, event_id)
    fields = body.model_dump(exclude_unset=True)
    if not is_staff(user):
        blocked = set(fields) - CUSTOMER_EDITABLE
        if blocked:
            raise HTTPException(403, "Deze gegevens kunnen alleen door White Vision worden aangepast")
    if user["role"] == "dj":
        fields.pop("dj_id", None)
        fields.pop("customer_id", None)
    _validate(fields)
    fields["updated_at"] = now()
    await db.events.update_one({"_id": ev["_id"]}, {"$set": fields})
    return await enrich_event(await db.events.find_one({"_id": ev["_id"]}), user)


@router.delete("/events/{event_id}")
async def delete_event(event_id: str, user: dict = Depends(require_admin)):
    ev = await get_event_for(user, event_id)
    async for f in db.files.find({"event_id": event_id}):
        await fs.delete(ObjectId(f["gridfs_id"]))
    for col in ("files", "messages", "music_items", "timeline_items", "invitations"):
        await db[col].delete_many({"event_id": event_id})
    await db.events.delete_one({"_id": ev["_id"]})
    return {"ok": True}
