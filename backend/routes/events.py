from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import event_scope, get_current_user, get_event_for, is_staff, now, require_admin
from database import get_session
from models import Event
from schemas import CUSTOMER_EDITABLE, EVENT_STATUSES, EventCreate, EventFields, EventOut
from services import enrich_event

router = APIRouter(tags=["events"])


def _validate(fields: dict):
    if "status" in fields and fields["status"] not in EVENT_STATUSES:
        raise HTTPException(400, "Ongeldige status")


@router.get("/events")
async def list_events(user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    scope = event_scope(user)
    stmt = select(Event).order_by(Event.date.asc().nulls_last())
    if scope is not None:
        stmt = stmt.where(scope)
    docs = (await session.scalars(stmt)).all()
    return [await enrich_event(session, d, user) for d in docs]


@router.post("/events")
async def create_event(body: EventCreate, user: dict = Depends(require_admin),
                       session: AsyncSession = Depends(get_session)):
    fields = body.model_dump(exclude_none=True)
    _validate(fields)
    event = Event(**fields, created_at=now(), updated_at=now())
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return await enrich_event(session, event, user)


@router.get("/events/{event_id}")
async def get_event(event_id: str, user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await enrich_event(session, await get_event_for(session, user, event_id), user)


@router.patch("/events/{event_id}")
async def update_event(event_id: str, body: EventFields, user: dict = Depends(get_current_user),
                       session: AsyncSession = Depends(get_session)):
    ev = await get_event_for(session, user, event_id)
    fields = body.model_dump(exclude_unset=True)
    if not is_staff(user):
        blocked = set(fields) - CUSTOMER_EDITABLE
        if blocked:
            raise HTTPException(403, "Deze gegevens kunnen alleen door White Vision worden aangepast")
    if user["role"] == "dj":
        fields.pop("dj_id", None)
        fields.pop("customer_id", None)
    _validate(fields)
    for key, value in fields.items():
        setattr(ev, key, value)
    ev.updated_at = now()
    await session.commit()
    await session.refresh(ev)
    return await enrich_event(session, ev, user)


@router.delete("/events/{event_id}")
async def delete_event(event_id: str, user: dict = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    ev = await get_event_for(session, user, event_id)
    await session.delete(ev)
    await session.commit()
    return {"ok": True}
