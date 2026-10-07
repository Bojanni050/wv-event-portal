from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core import (event_scope, get_child_for, get_current_user, get_event_for, is_staff, now, to_uuid,
                  touch_event, unread_filter)
from database import get_session
from models import Event, FileMeta, Message
from schemas import MessageIn, MessageOut, PinIn

router = APIRouter(tags=["messages"])


@router.get("/events/{event_id}/messages")
async def list_messages(event_id: str, user: dict = Depends(get_current_user),
                        session: AsyncSession = Depends(get_session)):
    ev = await get_event_for(session, user, event_id)
    flag = "read_by_staff" if is_staff(user) else "read_by_customer"
    column = getattr(Message, flag)
    await session.execute(update(Message).where(Message.event_id == ev.id, column.is_(False)).values({column: True}))
    await session.commit()
    docs = (await session.scalars(select(Message).where(Message.event_id == ev.id).order_by(Message.created_at.asc()))).all()
    return [MessageOut.model_validate(d) for d in docs]


@router.post("/events/{event_id}/messages")
async def send_message(event_id: str, body: MessageIn, user: dict = Depends(get_current_user),
                       session: AsyncSession = Depends(get_session)):
    ev = await get_event_for(session, user, event_id)
    text = body.text.strip()
    if not text and not body.attachment_file_id:
        raise HTTPException(400, "Bericht is leeg")
    attachment = None
    if body.attachment_file_id:
        f = await session.get(FileMeta, to_uuid(body.attachment_file_id))
        if not f or f.event_id != ev.id:
            raise HTTPException(400, "Bijlage niet gevonden")
        attachment = {"file_id": str(f.id), "filename": f.filename,
                      "content_type": f.content_type, "size": f.size}
    staff = is_staff(user)
    msg = Message(event_id=ev.id, sender_id=user["id"], sender_name=user["name"], sender_role=user["role"],
                  text=text, attachment=attachment, read_by_staff=staff, read_by_customer=not staff,
                  created_at=now())
    session.add(msg)
    await touch_event(session, ev.id)
    await session.commit()
    await session.refresh(msg)
    return MessageOut.model_validate(msg)


@router.patch("/messages/{message_id}")
async def pin_message(message_id: str, body: PinIn, user: dict = Depends(get_current_user),
                      session: AsyncSession = Depends(get_session)):
    doc = await get_child_for(session, Message, user, message_id)
    doc.pinned = body.pinned
    await session.commit()
    return MessageOut.model_validate(doc)


@router.get("/notifications")
async def notifications(user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    scope = event_scope(user)
    stmt = select(Event)
    if scope is not None:
        stmt = stmt.where(scope)
    events = (await session.scalars(stmt)).all()
    items, total = [], 0
    for ev in events:
        n = await session.scalar(select(func.count()).select_from(Message)
                                 .where(Message.event_id == ev.id, unread_filter(user)))
        if n:
            items.append({"event_id": str(ev.id), "title": ev.title, "unread": n})
            total += n
    return {"total": total, "events": items}
