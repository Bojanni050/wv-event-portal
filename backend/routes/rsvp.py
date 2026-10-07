from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import get_child_for, get_current_user, get_event_for, now, touch_event
from database import get_session
from models import Invitation, Rsvp
from schemas import RsvpIn, RsvpOut

router = APIRouter(tags=["rsvp"])
MAX_PER_EVENT = 1000


@router.post("/public/invitations/{token}/rsvp")
async def submit_rsvp(token: str, body: RsvpIn, session: AsyncSession = Depends(get_session)):
    inv = await session.scalar(select(Invitation).where(Invitation.share_token == token))
    if not inv:
        raise HTTPException(404, "Uitnodiging niet gevonden")
    if not inv.rsvp_enabled:
        raise HTTPException(400, "Aanmelden is gesloten")
    if body.attending not in {"yes", "no", "maybe"}:
        raise HTTPException(400, "Kies of je komt")
    if not body.name.strip():
        raise HTTPException(400, "Vul je naam in")
    count = await session.scalar(select(func.count()).select_from(Rsvp).where(Rsvp.event_id == inv.event_id))
    if count >= MAX_PER_EVENT:
        raise HTTPException(400, "Maximum aantal reacties bereikt")
    fields = body.model_dump()
    fields["name"] = fields["name"].strip()
    if fields["attending"] == "no":
        fields["guests"] = 0
    rsvp = Rsvp(event_id=inv.event_id, **fields, created_at=now())
    session.add(rsvp)
    await touch_event(session, inv.event_id)
    await session.commit()
    return {"ok": True, "name": rsvp.name, "attending": rsvp.attending}


@router.get("/events/{event_id}/rsvps")
async def list_rsvps(event_id: str, user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    ev = await get_event_for(session, user, event_id)
    docs = (await session.scalars(select(Rsvp).where(Rsvp.event_id == ev.id)
                                  .order_by(Rsvp.created_at.desc()).limit(MAX_PER_EVENT))).all()
    return [RsvpOut.model_validate(d) for d in docs]


@router.delete("/rsvps/{rsvp_id}")
async def delete_rsvp(rsvp_id: str, user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    doc = await get_child_for(session, Rsvp, user, rsvp_id)
    await session.delete(doc)
    await session.commit()
    return {"ok": True}
