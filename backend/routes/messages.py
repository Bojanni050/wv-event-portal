from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import (db, event_scope, get_child_for, get_current_user, get_event_for, is_staff, now, oid,
                  touch_event, unread_filter)
from models import Message

router = APIRouter(tags=["messages"])


class MessageIn(BaseModel):
    text: str = ""
    attachment_file_id: Optional[str] = None


class PinIn(BaseModel):
    pinned: bool


@router.get("/events/{event_id}/messages")
async def list_messages(event_id: str, user: dict = Depends(get_current_user)):
    await get_event_for(user, event_id)
    flag = "read_by_staff" if is_staff(user) else "read_by_customer"
    await db.messages.update_many({"event_id": event_id, flag: False}, {"$set": {flag: True}})
    docs = await db.messages.find({"event_id": event_id}).sort("created_at", 1).to_list(5000)
    return [Message.from_mongo(d).out() for d in docs]


@router.post("/events/{event_id}/messages")
async def send_message(event_id: str, body: MessageIn, user: dict = Depends(get_current_user)):
    await get_event_for(user, event_id)
    text = body.text.strip()
    if not text and not body.attachment_file_id:
        raise HTTPException(400, "Bericht is leeg")
    attachment = None
    if body.attachment_file_id:
        f = await db.files.find_one({"_id": oid(body.attachment_file_id), "event_id": event_id})
        if not f:
            raise HTTPException(400, "Bijlage niet gevonden")
        attachment = {"file_id": str(f["_id"]), "filename": f["filename"],
                      "content_type": f["content_type"], "size": f["size"]}
    staff = is_staff(user)
    msg = Message(event_id=event_id, sender_id=user["id"], sender_name=user["name"], sender_role=user["role"],
                  text=text, attachment=attachment, read_by_staff=staff, read_by_customer=not staff,
                  created_at=now())
    res = await db.messages.insert_one(msg.to_mongo())
    msg.id = str(res.inserted_id)
    await touch_event(event_id)
    return msg.out()


@router.patch("/messages/{message_id}")
async def pin_message(message_id: str, body: PinIn, user: dict = Depends(get_current_user)):
    doc = await get_child_for(user, "messages", message_id)
    await db.messages.update_one({"_id": doc["_id"]}, {"$set": {"pinned": body.pinned}})
    return Message.from_mongo({**doc, "pinned": body.pinned}).out()


@router.get("/notifications")
async def notifications(user: dict = Depends(get_current_user)):
    events = await db.events.find(event_scope(user), {"title": 1}).to_list(1000)
    items, total = [], 0
    for ev in events:
        n = await db.messages.count_documents({"event_id": str(ev["_id"]), **unread_filter(user)})
        if n:
            items.append({"event_id": str(ev["_id"]), "title": ev["title"], "unread": n})
            total += n
    return {"total": total, "events": items}
