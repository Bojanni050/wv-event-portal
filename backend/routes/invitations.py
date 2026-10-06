import secrets

from fastapi import APIRouter, Depends, HTTPException

from core import db, get_current_user, get_event_for, is_staff, now, oid, require_admin, touch_event
from models import Invitation, InvitationFields, InvitationTemplate, TemplateFields
from routes.files import read_file

router = APIRouter(tags=["invitations"])


@router.get("/events/{event_id}/invitation")
async def get_invitation(event_id: str, user: dict = Depends(get_current_user)):
    await get_event_for(user, event_id)
    doc = await db.invitations.find_one({"event_id": event_id})
    return Invitation.from_mongo(doc).out() if doc else None


@router.put("/events/{event_id}/invitation")
async def save_invitation(event_id: str, body: InvitationFields, user: dict = Depends(get_current_user)):
    await get_event_for(user, event_id)
    if body.photo_file_id and not await db.files.find_one({"_id": oid(body.photo_file_id), "event_id": event_id}):
        raise HTTPException(400, "Foto niet gevonden")
    fields = {**body.model_dump(), "updated_at": now()}
    await db.invitations.update_one({"event_id": event_id}, {"$set": fields}, upsert=True)
    await touch_event(event_id)
    return Invitation.from_mongo(await db.invitations.find_one({"event_id": event_id})).out()


@router.post("/events/{event_id}/invitation/share")
async def share_invitation(event_id: str, user: dict = Depends(get_current_user)):
    await get_event_for(user, event_id)
    doc = await db.invitations.find_one({"event_id": event_id})
    if not doc:
        raise HTTPException(400, "Sla de uitnodiging eerst op")
    token = doc.get("share_token") or secrets.token_urlsafe(10)
    await db.invitations.update_one({"_id": doc["_id"]}, {"$set": {"share_token": token}})
    return {"share_token": token}


@router.get("/public/invitations/{token}")
async def public_invitation(token: str):
    doc = await db.invitations.find_one({"share_token": token})
    if not doc:
        raise HTTPException(404, "Uitnodiging niet gevonden")
    data = Invitation.from_mongo(doc).out()
    data.pop("event_id", None)
    return data


@router.get("/public/invitations/{token}/photo")
async def public_invitation_photo(token: str):
    doc = await db.invitations.find_one({"share_token": token})
    if not doc or not doc.get("photo_file_id"):
        raise HTTPException(404, "Geen foto")
    meta = await db.files.find_one({"_id": oid(doc["photo_file_id"])})
    if not meta:
        raise HTTPException(404, "Geen foto")
    return await read_file(meta)


@router.get("/invitation-templates")
async def list_templates(user: dict = Depends(get_current_user)):
    query = {} if is_staff(user) else {"active": True}
    docs = await db.invitation_templates.find(query).sort("created_at", 1).to_list(200)
    return [InvitationTemplate.from_mongo(d).out() for d in docs]


@router.post("/invitation-templates")
async def create_template(body: TemplateFields, user: dict = Depends(require_admin)):
    tpl = InvitationTemplate(**body.model_dump(), created_at=now())
    res = await db.invitation_templates.insert_one(tpl.to_mongo())
    tpl.id = str(res.inserted_id)
    return tpl.out()


@router.put("/invitation-templates/{template_id}")
async def update_template(template_id: str, body: TemplateFields, user: dict = Depends(require_admin)):
    res = await db.invitation_templates.update_one({"_id": oid(template_id)}, {"$set": body.model_dump()})
    if not res.matched_count:
        raise HTTPException(404, "Sjabloon niet gevonden")
    return InvitationTemplate.from_mongo(await db.invitation_templates.find_one({"_id": oid(template_id)})).out()


@router.delete("/invitation-templates/{template_id}")
async def delete_template(template_id: str, user: dict = Depends(require_admin)):
    await db.invitation_templates.delete_one({"_id": oid(template_id)})
    return {"ok": True}
