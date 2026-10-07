import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import get_current_user, get_event_for, is_staff, now, require_admin, to_uuid, touch_event
from database import get_session
from models import FileMeta, Invitation, InvitationTemplate
from schemas import InvitationFields, InvitationOut, TemplateFields, TemplateOut
from routes.files import read_file

router = APIRouter(tags=["invitations"])


@router.get("/events/{event_id}/invitation")
async def get_invitation(event_id: str, user: dict = Depends(get_current_user),
                         session: AsyncSession = Depends(get_session)):
    ev = await get_event_for(session, user, event_id)
    doc = await session.scalar(select(Invitation).where(Invitation.event_id == ev.id))
    return InvitationOut.model_validate(doc) if doc else None


@router.put("/events/{event_id}/invitation")
async def save_invitation(event_id: str, body: InvitationFields, user: dict = Depends(get_current_user),
                          session: AsyncSession = Depends(get_session)):
    ev = await get_event_for(session, user, event_id)
    if body.photo_file_id:
        f = await session.get(FileMeta, to_uuid(body.photo_file_id))
        if not f or f.event_id != ev.id:
            raise HTTPException(400, "Foto niet gevonden")
    doc = await session.scalar(select(Invitation).where(Invitation.event_id == ev.id))
    if not doc:
        doc = Invitation(event_id=ev.id)
        session.add(doc)
    for key, value in body.model_dump().items():
        setattr(doc, key, value)
    doc.updated_at = now()
    await touch_event(session, ev.id)
    await session.commit()
    await session.refresh(doc)
    return InvitationOut.model_validate(doc)


@router.post("/events/{event_id}/invitation/share")
async def share_invitation(event_id: str, user: dict = Depends(get_current_user),
                           session: AsyncSession = Depends(get_session)):
    ev = await get_event_for(session, user, event_id)
    doc = await session.scalar(select(Invitation).where(Invitation.event_id == ev.id))
    if not doc:
        raise HTTPException(400, "Sla de uitnodiging eerst op")
    token = doc.share_token or secrets.token_urlsafe(10)
    doc.share_token = token
    await session.commit()
    return {"share_token": token}


@router.get("/public/invitations/{token}")
async def public_invitation(token: str, session: AsyncSession = Depends(get_session)):
    doc = await session.scalar(select(Invitation).where(Invitation.share_token == token))
    if not doc:
        raise HTTPException(404, "Uitnodiging niet gevonden")
    data = InvitationOut.model_validate(doc).model_dump(mode="json")
    data.pop("event_id", None)
    return data


@router.get("/public/invitations/{token}/photo")
async def public_invitation_photo(token: str, session: AsyncSession = Depends(get_session)):
    doc = await session.scalar(select(Invitation).where(Invitation.share_token == token))
    if not doc or not doc.photo_file_id:
        raise HTTPException(404, "Geen foto")
    meta = await session.get(FileMeta, to_uuid(doc.photo_file_id))
    if not meta:
        raise HTTPException(404, "Geen foto")
    return read_file(meta)


@router.get("/invitation-templates")
async def list_templates(user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    stmt = select(InvitationTemplate).order_by(InvitationTemplate.created_at.asc())
    if not is_staff(user):
        stmt = stmt.where(InvitationTemplate.active.is_(True))
    docs = (await session.scalars(stmt)).all()
    return [TemplateOut.model_validate(d) for d in docs]


@router.post("/invitation-templates")
async def create_template(body: TemplateFields, user: dict = Depends(require_admin),
                          session: AsyncSession = Depends(get_session)):
    tpl = InvitationTemplate(**body.model_dump(), created_at=now())
    session.add(tpl)
    await session.commit()
    await session.refresh(tpl)
    return TemplateOut.model_validate(tpl)


@router.put("/invitation-templates/{template_id}")
async def update_template(template_id: str, body: TemplateFields, user: dict = Depends(require_admin),
                          session: AsyncSession = Depends(get_session)):
    tpl = await session.get(InvitationTemplate, to_uuid(template_id))
    if not tpl:
        raise HTTPException(404, "Sjabloon niet gevonden")
    for key, value in body.model_dump().items():
        setattr(tpl, key, value)
    await session.commit()
    return TemplateOut.model_validate(tpl)


@router.delete("/invitation-templates/{template_id}")
async def delete_template(template_id: str, user: dict = Depends(require_admin),
                          session: AsyncSession = Depends(get_session)):
    tpl = await session.get(InvitationTemplate, to_uuid(template_id))
    if tpl:
        await session.delete(tpl)
        await session.commit()
    return {"ok": True}
