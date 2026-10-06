import logging
import secrets
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import db, event_scope, hash_password, now, oid, require_admin, require_staff, unread_filter
from mailer import send_email, welcome_email_html
from models import DJ, Customer, Message, User
from routes.auth import WELCOME_TTL, issue_password_link
from services import enrich_event

router = APIRouter(tags=["admin"])
log = logging.getLogger(__name__)
MONTHS = ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september",
          "oktober", "november", "december"]


class PersonIn(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    bio: Optional[str] = None
    password: Optional[str] = None
    send_welcome: bool = False


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


def _event_line(ev: Optional[dict]) -> str:
    if not ev:
        return ""
    if not ev.get("date"):
        return ev["title"]
    d = date.fromisoformat(ev["date"])
    return f"{ev['title']} · {d.day} {MONTHS[d.month - 1]} {d.year}"


async def _send_welcome(customer: dict):
    cid = str(customer["_id"])
    if not customer.get("email"):
        raise HTTPException(400, "Deze klant heeft geen e-mailadres")
    uid = customer.get("user_id")
    if not uid:
        uid = await _create_login(customer["email"], secrets.token_urlsafe(32), customer["name"], "customer",
                                  {"customer_id": cid})
        await db.customers.update_one({"_id": customer["_id"]}, {"$set": {"user_id": uid}})
    recent = await db.password_reset_tokens.count_documents(
        {"user_id": uid, "purpose": "welcome", "created_at": {"$gt": now() - timedelta(hours=1)}})
    if recent >= 3:
        raise HTTPException(429, "Er zijn het afgelopen uur al 3 welkomstmails verstuurd")
    user = await db.users.find_one({"_id": oid(uid)})
    ev = await db.events.find_one({"customer_id": cid}, sort=[("date", 1)])
    link = await issue_password_link(uid, WELCOME_TTL, "welcome")
    try:
        await send_email(to=user["email"], subject="Welkom bij White Vision, je event-omgeving staat klaar",
                         html=welcome_email_html(customer["name"], link, _event_line(ev)))
    except Exception as e:
        log.error("Welcome email failed for customer %s: %s", cid, e)
        raise HTTPException(502, "Welkomstmail kon niet worden verstuurd")
    await db.customers.update_one({"_id": customer["_id"]}, {"$set": {"welcome_sent_at": now()}})


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
        uid = await _create_login(email, None if body.send_welcome else body.password, body.name, "customer",
                                  {"customer_id": cid})
    except HTTPException:
        await db.customers.delete_one({"_id": res.inserted_id})
        raise
    if uid:
        await db.customers.update_one({"_id": res.inserted_id}, {"$set": {"user_id": uid}})
    welcome_error = None
    if body.send_welcome and email:
        try:
            await _send_welcome(await db.customers.find_one({"_id": res.inserted_id}))
        except HTTPException as e:
            if e.status_code == 400 and "account" in str(e.detail):
                await db.customers.delete_one({"_id": res.inserted_id})
                raise
            welcome_error = e.detail
    data = await _person_out(Customer, await db.customers.find_one({"_id": res.inserted_id}))
    data["welcome_error"] = welcome_error
    return data


@router.post("/customers/{customer_id}/welcome")
async def send_customer_welcome(customer_id: str, user: dict = Depends(require_admin)):
    doc = await db.customers.find_one({"_id": oid(customer_id)})
    if not doc:
        raise HTTPException(404, "Klant niet gevonden")
    await _send_welcome(doc)
    return await _person_out(Customer, await db.customers.find_one({"_id": doc["_id"]}))


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
