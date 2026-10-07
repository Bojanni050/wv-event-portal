import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import get_child_for, get_current_user, get_event_for, is_staff, now, touch_event
from database import get_session
from models import TimelineItem
from schemas import TimelineIn, TimelineItemOut, TimelineUpdate

router = APIRouter(tags=["timeline"])
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def sort_key(item: TimelineItem):
    return (item.time < "06:00", item.time)


def _check(fields: dict, staff: bool):
    if "time" in fields and not TIME_RE.match(fields["time"] or ""):
        raise HTTPException(400, "Gebruik een tijd als 20:30")
    if "status" in fields:
        if not staff:
            raise HTTPException(403, "Alleen White Vision kan onderdelen bevestigen")
        if fields["status"] not in {"suggested", "confirmed"}:
            raise HTTPException(400, "Ongeldige status")


@router.get("/events/{event_id}/timeline")
async def list_timeline(event_id: str, user: dict = Depends(get_current_user),
                        session: AsyncSession = Depends(get_session)):
    ev = await get_event_for(session, user, event_id)
    docs = (await session.scalars(select(TimelineItem).where(TimelineItem.event_id == ev.id))).all()
    docs = sorted(docs, key=sort_key)
    return [TimelineItemOut.model_validate(d) for d in docs]


@router.post("/events/{event_id}/timeline")
async def add_timeline(event_id: str, body: TimelineIn, user: dict = Depends(get_current_user),
                       session: AsyncSession = Depends(get_session)):
    ev = await get_event_for(session, user, event_id)
    staff = is_staff(user)
    fields = body.model_dump(exclude_none=True)
    _check(fields, staff)
    fields["status"] = fields.get("status") or ("confirmed" if staff else "suggested")
    item = TimelineItem(event_id=ev.id, **fields, created_by_role=user["role"], created_at=now())
    session.add(item)
    await touch_event(session, ev.id)
    await session.commit()
    await session.refresh(item)
    return TimelineItemOut.model_validate(item)


@router.patch("/timeline/{item_id}")
async def update_timeline(item_id: str, body: TimelineUpdate, user: dict = Depends(get_current_user),
                          session: AsyncSession = Depends(get_session)):
    doc = await get_child_for(session, TimelineItem, user, item_id)
    staff = is_staff(user)
    if not staff and doc.status != "suggested":
        raise HTTPException(403, "Definitieve onderdelen kunnen alleen door White Vision worden gewijzigd")
    fields = body.model_dump(exclude_unset=True)
    _check(fields, staff)
    for key, value in fields.items():
        setattr(doc, key, value)
    await touch_event(session, doc.event_id)
    await session.commit()
    return TimelineItemOut.model_validate(doc)


@router.delete("/timeline/{item_id}")
async def delete_timeline(item_id: str, user: dict = Depends(get_current_user),
                          session: AsyncSession = Depends(get_session)):
    doc = await get_child_for(session, TimelineItem, user, item_id)
    if not is_staff(user) and doc.status != "suggested":
        raise HTTPException(403, "Definitieve onderdelen kunnen alleen door White Vision worden verwijderd")
    await session.delete(doc)
    await touch_event(session, doc.event_id)
    await session.commit()
    return {"ok": True}
