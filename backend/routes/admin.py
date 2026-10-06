from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import db, event_scope, hash_password, now, oid, require_admin, require_staff, unread_filter
from models import DJ, Customer, Message, User
from services import enrich_event

router = APIRouter(tags=["admin"])


class PersonIn(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    bio: Optional[str] = None
    password: Optional[str] = None


async def _create_login(email: Optional[str], password: Optional[str], name: str, role: str, link: dict):
    if not password:
        return None
    if not email:
        raise HTTPException(400, "E-mailadres is verplicht voor een login")
    if len(password) < 8:
        raise HTTPException(400, "Wachtwoord moet minimaal 8 tekens hebben")
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Er bestaat al een account met dit e-mailadres")
    res = await db.users.insert_one({"email": email, "name": name, "role": role, "created_at": now(),
                                     "password_hash": hash_password(password), **link})
    return str(res.inserted_id)


async def _person_out(model, doc):
    data = model.from_mongo(doc).out()
    data["has_login"] = bool(doc.get("user_id"))
    return data


@router.get("/customers")
async def list_customers(user: dict = Depends(require_staff)):
    docs = await db.customers.find().sort("name", 1).to_list(2000)
    out = []
    for d in docs:
        data = await _person_out(Customer, d)
        data["event_count"] = await db.events.count_documents({"customer_id": str(d["_id"])})
        out.append(data)
    return out


@router.post("/customers")
async def create_customer(body: PersonIn, user: dict = Depends(require_admin)):
    email = body.email.strip().lower() if body.email else None
    res = await db.customers.insert_one(Customer(name=body.name, email=email, phone=body.phone,
                                                 notes=body.notes, created_at=now()).to_mongo())
    cid = str(res.inserted_id)
    try:
        uid = await _create_login(email, body.password, body.name, "customer", {"customer_id": cid})
    except HTTPException:
        await db.customers.delete_one({"_id": res.inserted_id})
        raise
    if uid:
        await db.customers.update_one({"_id": res.inserted_id}, {"$set": {"user_id": uid}})
    return await _person_out(Customer, await db.customers.find_one({"_id": res.inserted_id}))


@router.patch("/customers/{customer_id}")
async def update_customer(customer_id: str, body: PersonIn, user: dict = Depends(require_admin)):
    doc = await db.customers.find_one({"_id": oid(customer_id)})
    if not doc:
        raise HTTPException(404, "Klant niet gevonden")
    email = body.email.strip().lower() if body.email else None
    await db.customers.update_one({"_id": doc["_id"]}, {"$set": {"name": body.name, "email": email,
                                                                  "phone": body.phone, "notes": body.notes}})
    if body.password and not doc.get("user_id"):
        uid = await _create_login(email, body.password, body.name, "customer", {"customer_id": customer_id})
        await db.customers.update_one({"_id": doc["_id"]}, {"$set": {"user_id": uid}})
    return await _person_out(Customer, await db.customers.find_one({"_id": doc["_id"]}))


@router.delete("/customers/{customer_id}")
async def delete_customer(customer_id: str, user: dict = Depends(require_admin)):
    if await db.events.count_documents({"customer_id": customer_id}):
        raise HTTPException(400, "Deze klant heeft nog events")
    await db.users.delete_many({"customer_id": customer_id})
    await db.customers.delete_one({"_id": oid(customer_id)})
    return {"ok": True}


@router.get("/djs")
async def list_djs(user: dict = Depends(require_staff)):
    docs = await db.djs.find().sort("name", 1).to_list(500)
    out = []
    for d in docs:
        data = await _person_out(DJ, d)
        data["event_count"] = await db.events.count_documents({"dj_id": str(d["_id"])})
        out.append(data)
    return out


@router.post("/djs")
async def create_dj(body: PersonIn, user: dict = Depends(require_admin)):
    email = body.email.strip().lower() if body.email else None
    res = await db.djs.insert_one(DJ(name=body.name, email=email, phone=body.phone, bio=body.bio,
                                     created_at=now()).to_mongo())
    did = str(res.inserted_id)
    try:
        uid = await _create_login(email, body.password, body.name, "dj", {"dj_id": did})
    except HTTPException:
        await db.djs.delete_one({"_id": res.inserted_id})
        raise
    if uid:
        await db.djs.update_one({"_id": res.inserted_id}, {"$set": {"user_id": uid}})
    return await _person_out(DJ, await db.djs.find_one({"_id": res.inserted_id}))


@router.patch("/djs/{dj_id}")
async def update_dj(dj_id: str, body: PersonIn, user: dict = Depends(require_admin)):
    doc = await db.djs.find_one({"_id": oid(dj_id)})
    if not doc:
        raise HTTPException(404, "DJ niet gevonden")
    email = body.email.strip().lower() if body.email else None
    await db.djs.update_one({"_id": doc["_id"]}, {"$set": {"name": body.name, "email": email,
                                                            "phone": body.phone, "bio": body.bio}})
    if body.password and not doc.get("user_id"):
        uid = await _create_login(email, body.password, body.name, "dj", {"dj_id": dj_id})
        await db.djs.update_one({"_id": doc["_id"]}, {"$set": {"user_id": uid}})
    return await _person_out(DJ, await db.djs.find_one({"_id": doc["_id"]}))


@router.get("/users")
async def list_users(user: dict = Depends(require_admin)):
    docs = await db.users.find().to_list(2000)
    return [User.from_mongo(d).out() for d in docs]


def _days_until(iso: Optional[str]) -> Optional[int]:
    if not iso:
        return None
    return (date.fromisoformat(iso) - date.today()).days


@router.get("/admin/overview")
async def overview(user: dict = Depends(require_staff)):
    docs = await db.events.find(event_scope(user)).to_list(1000)
    events = [await enrich_event(d, user) for d in docs]
    active = [e for e in events if e["status"] != "completed"]
    upcoming = sorted([e for e in active if (_days_until(e["date"]) or -1) >= 0], key=lambda e: e["date"])

    attention = []
    for e in active:
        reasons = []
        days = _days_until(e["date"])
        if e["unread"]:
            reasons.append(f"{e['unread']} ongelezen bericht(en)")
        if days is not None and 0 <= days <= 90 and e["progress"]["overall"] < 60:
            reasons.append(f"Over {days} dagen, pas {e['progress']['overall']}% klaar")
        if e["status"] == "new":
            reasons.append("Nog niet opgepakt")
        if not e.get("dj_id"):
            reasons.append("Geen DJ toegewezen")
        if reasons:
            attention.append({**e, "reasons": reasons})

    ids = [e["id"] for e in events]
    titles = {e["id"]: e["title"] for e in events}
    unread_docs = await db.messages.find({"event_id": {"$in": ids}, **unread_filter(user)}) \
        .sort("created_at", -1).to_list(10)
    unread = [{**Message.from_mongo(m).out(), "event_title": titles.get(m["event_id"])} for m in unread_docs]
    incomplete = [e for e in active if e["stats"]["missing_info"]]
    recent = sorted(events, key=lambda e: e["updated_at"] or e["created_at"], reverse=True)[:6]

    return {
        "counts": {"upcoming": len(upcoming), "attention": len(attention),
                   "unread": sum(e["unread"] for e in events), "incomplete": len(incomplete)},
        "upcoming": upcoming[:6], "attention": attention[:6], "unread_messages": unread,
        "incomplete": incomplete[:6], "recent": recent,
    }
