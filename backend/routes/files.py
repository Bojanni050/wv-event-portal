from urllib.parse import quote

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

from core import db, fs, get_child_for, get_current_user, get_event_for, is_staff, now, touch_event
from models import FileMeta

router = APIRouter(tags=["files"])
MAX_SIZE = 15 * 1024 * 1024
CATEGORIES = {"document", "image", "chat", "invitation"}
DOC_TYPES = {
    "application/pdf", "application/msword", "text/plain", "text/csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


async def read_file(meta: dict) -> Response:
    stream = await fs.open_download_stream(ObjectId(meta["gridfs_id"]))
    data = await stream.read()
    return Response(content=data, media_type=meta["content_type"], headers={
        "Content-Disposition": f"inline; filename*=UTF-8''{quote(meta['filename'])}",
        "Cache-Control": "private, max-age=3600"})


@router.get("/events/{event_id}/files")
async def list_files(event_id: str, user: dict = Depends(get_current_user)):
    await get_event_for(user, event_id)
    docs = await db.files.find({"event_id": event_id}).sort("created_at", -1).to_list(2000)
    return [FileMeta.from_mongo(d).out() for d in docs]


@router.post("/events/{event_id}/files")
async def upload_file(event_id: str, file: UploadFile = File(...), category: str = Form("document"),
                      user: dict = Depends(get_current_user)):
    await get_event_for(user, event_id)
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
    gridfs_id = await fs.upload_from_stream(file.filename or "bestand", data, metadata={"event_id": event_id})
    meta = FileMeta(event_id=event_id, filename=file.filename or "bestand", content_type=content_type,
                    size=len(data), category=category, gridfs_id=str(gridfs_id), uploaded_by=user["id"],
                    uploaded_by_name=user["name"], uploaded_by_role=user["role"], created_at=now())
    res = await db.files.insert_one(meta.to_mongo())
    meta.id = str(res.inserted_id)
    await touch_event(event_id)
    return meta.out()


@router.get("/files/{file_id}/download")
async def download_file(file_id: str, user: dict = Depends(get_current_user)):
    return await read_file(await get_child_for(user, "files", file_id))


@router.delete("/files/{file_id}")
async def delete_file(file_id: str, user: dict = Depends(get_current_user)):
    doc = await get_child_for(user, "files", file_id)
    if not is_staff(user) and doc["uploaded_by"] != user["id"]:
        raise HTTPException(403, "Je kunt alleen je eigen bestanden verwijderen")
    await fs.delete(ObjectId(doc["gridfs_id"]))
    await db.files.delete_one({"_id": doc["_id"]})
    return {"ok": True}
