from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import get_child_for, get_current_user, get_event_for, now, touch_event
from database import get_session
from models import MusicItem
from schemas import MusicIn, MusicItemOut, MusicUpdate

router = APIRouter(tags=["music"])
CATEGORIES = {"must_play", "dont_play", "favorite", "special"}


@router.get("/events/{event_id}/music")
async def list_music(event_id: str, user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    ev = await get_event_for(session, user, event_id)
    docs = (await session.scalars(select(MusicItem).where(MusicItem.event_id == ev.id).order_by(MusicItem.created_at.asc()))).all()
    return [MusicItemOut.model_validate(d) for d in docs]


@router.post("/events/{event_id}/music")
async def add_music(event_id: str, body: MusicIn, user: dict = Depends(get_current_user),
                    session: AsyncSession = Depends(get_session)):
    ev = await get_event_for(session, user, event_id)
    if body.category not in CATEGORIES:
        raise HTTPException(400, "Ongeldige categorie")
    if not body.title.strip():
        raise HTTPException(400, "Titel is verplicht")
    item = MusicItem(event_id=ev.id, **body.model_dump(), added_by_role=user["role"], created_at=now())
    session.add(item)
    await touch_event(session, ev.id)
    await session.commit()
    await session.refresh(item)
    return MusicItemOut.model_validate(item)


@router.patch("/music/{item_id}")
async def update_music(item_id: str, body: MusicUpdate, user: dict = Depends(get_current_user),
                       session: AsyncSession = Depends(get_session)):
    doc = await get_child_for(session, MusicItem, user, item_id)
    fields = body.model_dump(exclude_unset=True)
    if "category" in fields and fields["category"] not in CATEGORIES:
        raise HTTPException(400, "Ongeldige categorie")
    for key, value in fields.items():
        setattr(doc, key, value)
    await touch_event(session, doc.event_id)
    await session.commit()
    return MusicItemOut.model_validate(doc)


@router.delete("/music/{item_id}")
async def delete_music(item_id: str, user: dict = Depends(get_current_user),
                       session: AsyncSession = Depends(get_session)):
    doc = await get_child_for(session, MusicItem, user, item_id)
    await session.delete(doc)
    await touch_event(session, doc.event_id)
    await session.commit()
    return {"ok": True}
