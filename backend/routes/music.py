from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import db, get_child_for, get_current_user, get_event_for, now, touch_event
from models import MusicItem

router = APIRouter(tags=["music"])
CATEGORIES = {"must_play", "dont_play", "favorite", "special"}


class MusicIn(BaseModel):
    category: str
    title: str
    artist: Optional[str] = None
    notes: Optional[str] = None
    moment: Optional[str] = None


class MusicUpdate(BaseModel):
    category: Optional[str] = None
    title: Optional[str] = None
    artist: Optional[str] = None
    notes: Optional[str] = None
    moment: Optional[str] = None


@router.get("/events/{event_id}/music")
async def list_music(event_id: str, user: dict = Depends(get_current_user)):
    await get_event_for(user, event_id)
    docs = await db.music_items.find({"event_id": event_id}).sort("created_at", 1).to_list(2000)
    return [MusicItem.from_mongo(d).out() for d in docs]


@router.post("/events/{event_id}/music")
async def add_music(event_id: str, body: MusicIn, user: dict = Depends(get_current_user)):
    await get_event_for(user, event_id)
    if body.category not in CATEGORIES:
        raise HTTPException(400, "Ongeldige categorie")
    if not body.title.strip():
        raise HTTPException(400, "Titel is verplicht")
    item = MusicItem(event_id=event_id, **body.model_dump(), added_by_role=user["role"], created_at=now())
    res = await db.music_items.insert_one(item.to_mongo())
    item.id = str(res.inserted_id)
    await touch_event(event_id)
    return item.out()


@router.patch("/music/{item_id}")
async def update_music(item_id: str, body: MusicUpdate, user: dict = Depends(get_current_user)):
    doc = await get_child_for(user, "music_items", item_id)
    fields = body.model_dump(exclude_unset=True)
    if "category" in fields and fields["category"] not in CATEGORIES:
        raise HTTPException(400, "Ongeldige categorie")
    await db.music_items.update_one({"_id": doc["_id"]}, {"$set": fields})
    await touch_event(doc["event_id"])
    return MusicItem.from_mongo({**doc, **fields}).out()


@router.delete("/music/{item_id}")
async def delete_music(item_id: str, user: dict = Depends(get_current_user)):
    doc = await get_child_for(user, "music_items", item_id)
    await db.music_items.delete_one({"_id": doc["_id"]})
    await touch_event(doc["event_id"])
    return {"ok": True}
