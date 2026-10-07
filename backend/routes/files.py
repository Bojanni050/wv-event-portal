from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import get_child_for, get_current_user, get_event_for, is_staff, now, touch_event
from database import get_session
from models import FileMeta
from schemas import FileOut

router = APIRouter(tags=["files"])
MAX_SIZE = 15 * 1024 * 1024
CATEGORIES = {"document", "image", "chat", "invitation"}
DOC_TYPES = {
    "application/pdf", "application/msword", "text/plain", "text/csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def read_file(meta: FileMeta) -> Response:
    return Response(content=meta.data, media_type=meta.content_type, headers={
        "Content-Disposition": f"inline; filename*=UTF-8''{quote(meta.filename)}",
        "Cache-Control": "private, max-age=3600"})


@router.get("/events/{event_id}/files")
async def list_files(event_id: str, user: dict = Depends(get_current_user),
                     session: AsyncSession = Depends(get_session)):
    ev = await get_event_for(session, user, event_id)
    docs = (await session.scalars(select(FileMeta).where(FileMeta.event_id == ev.id).order_by(FileMeta.created_at.desc()))).all()
    return [FileOut.model_validate(d) for d in docs]


@router.post("/events/{event_id}/files")
async def upload_file(event_id: str, file: UploadFile = File(...), category: str = Form("document"),
                      user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    ev = await get_event_for(session, user, event_id)
    content_type = file.content_type or "application/octet-stream"
    if not (content_type.startswith("image/") or content_type in DOC_TYPES):
        raise HTTPException(400, "Alleen afbeeldingen, PDF's en documenten zijn toegestaan")
    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(413, "Bestand is groter dan 15 MB")
    if category not in CATEGORIES:
        category = "document"
    if category == "document" and content_type.startswith("image/"):
        category = "image"
    meta = FileMeta(event_id=ev.id, filename=file.filename or "bestand", content_type=content_type, size=len(data),
                    category=category, data=data, uploaded_by=user["id"], uploaded_by_name=user["name"],
                    uploaded_by_role=user["role"], created_at=now())
    session.add(meta)
    await touch_event(session, ev.id)
    await session.commit()
    await session.refresh(meta)
    return FileOut.model_validate(meta)


@router.get("/files/{file_id}/download")
async def download_file(file_id: str, user: dict = Depends(get_current_user),
                        session: AsyncSession = Depends(get_session)):
    return read_file(await get_child_for(session, FileMeta, user, file_id))


@router.delete("/files/{file_id}")
async def delete_file(file_id: str, user: dict = Depends(get_current_user),
                      session: AsyncSession = Depends(get_session)):
    doc = await get_child_for(session, FileMeta, user, file_id)
    if not is_staff(user) and doc.uploaded_by != user["id"]:
        raise HTTPException(403, "Je kunt alleen je eigen bestanden verwijderen")
    await session.delete(doc)
    await touch_event(session, doc.event_id)
    await session.commit()
    return {"ok": True}
