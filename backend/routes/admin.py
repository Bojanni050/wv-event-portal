import logging
import secrets
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import hash_password, now, require_admin, require_staff, to_uuid, unread_filter
from database import get_session
from mailer import send_email, welcome_email_html
from models import Customer, DJ, Event, Message, PasswordResetToken, User
from schemas import CustomerOut, DjOut, MessageOut, PersonIn, UserOut
from services import enrich_event
from routes.auth import WELCOME_TTL, issue_password_link

router = APIRouter(tags=["admin"])
log = logging.getLogger(__name__)
MONTHS = ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september",
          "oktober", "november", "december"]


async def _create_login(session: AsyncSession, email: Optional[str], password: Optional[str], name: str, role: str,
                        link: dict) -> Optional[str]:
    if not password:
        return None
    if not email:
        raise HTTPException(400, "E-mailadres is verplicht voor een login")
    if len(password) < 8:
        raise HTTPException(400, "Wachtwoord moet minimaal 8 tekens hebben")
    if await session.scalar(select(User).where(User.email == email)):
        raise HTTPException(400, "Er bestaat al een account met dit e-mailadres")
    user = User(email=email, name=name, role=role, created_at=now(),
                password_hash=hash_password(password), **link)
    session.add(user)
    await session.flush()
    return str(user.id)


def _person_out(model, doc) -> dict:
    data = model.model_validate(doc)
    data.has_login = bool(doc.user_id)
    return data


def _event_line(ev: Optional[Event]) -> str:
    if not ev:
        return ""
    if not ev.date:
        return ev.title
    return f"{ev.title} · {ev.date.day} {MONTHS[ev.date.month - 1]} {ev.date.year}"


async def _send_welcome(session: AsyncSession, customer: Customer):
    if not customer.email:
        raise HTTPException(400, "Deze klant heeft geen e-mailadres")
    uid = customer.user_id
    if not uid:
        uid_str = await _create_login(session, customer.email, secrets.token_urlsafe(32), customer.name, "customer",
                                      {"customer_id": customer.id})
        customer.user_id = to_uuid(uid_str)
        uid = customer.user_id
    recent = await session.scalar(select(func.count()).select_from(PasswordResetToken)
                                  .where(PasswordResetToken.user_id == uid, PasswordResetToken.purpose == "welcome",
                                         PasswordResetToken.created_at > now() - timedelta(hours=1)))
    if recent >= 3:
        raise HTTPException(429, "Er zijn het afgelopen uur al 3 welkomstmails verstuurd")
    user = await session.get(User, uid)
    ev = await session.scalar(select(Event).where(Event.customer_id == customer.id).order_by(Event.date.asc()).limit(1))
    link = await issue_password_link(session, uid, WELCOME_TTL, "welcome")
    try:
        await send_email(to=user.email, subject="Welkom bij White Vision, je event-omgeving staat klaar",
                         html=welcome_email_html(customer.name, link, _event_line(ev)))
    except Exception as e:  # noqa: BLE001
        log.error("Welcome email failed for customer %s: %s", customer.id, e)
        raise HTTPException(502, "Welkomstmail kon niet worden verstuurd")
    customer.welcome_sent_at = now()


@router.get("/customers")
async def list_customers(user: dict = Depends(require_staff), session: AsyncSession = Depends(get_session)):
    docs = (await session.scalars(select(Customer).order_by(Customer.name.asc()))).all()
    out = []
    for d in docs:
        data = _person_out(CustomerOut, d)
        data.event_count = await session.scalar(select(func.count()).select_from(Event).where(Event.customer_id == d.id))
        out.append(data)
    return out


@router.post("/customers")
async def create_customer(body: PersonIn, user: dict = Depends(require_admin),
                          session: AsyncSession = Depends(get_session)):
    email = body.email.strip().lower() if body.email else None
    customer = Customer(name=body.name, email=email, phone=body.phone, notes=body.notes, created_at=now())
    session.add(customer)
    await session.flush()
    try:
        uid = await _create_login(session, email, None if body.send_welcome else body.password, body.name, "customer",
                                  {"customer_id": customer.id})
    except HTTPException:
        await session.rollback()
        raise
    if uid:
        customer.user_id = to_uuid(uid)
    welcome_error = None
    if body.send_welcome and email:
        try:
            await _send_welcome(session, customer)
        except HTTPException as e:
            if e.status_code == 400 and "account" in str(e.detail):
                await session.rollback()
                raise
            welcome_error = e.detail
    await session.commit()
    data = _person_out(CustomerOut, await session.get(Customer, customer.id))
    data.welcome_error = welcome_error
    return data


@router.post("/customers/{customer_id}/welcome")
async def send_customer_welcome(customer_id: str, user: dict = Depends(require_admin),
                                session: AsyncSession = Depends(get_session)):
    doc = await session.get(Customer, to_uuid(customer_id))
    if not doc:
        raise HTTPException(404, "Klant niet gevonden")
    await _send_welcome(session, doc)
    await session.commit()
    return _person_out(CustomerOut, doc)


@router.patch("/customers/{customer_id}")
async def update_customer(customer_id: str, body: PersonIn, user: dict = Depends(require_admin),
                          session: AsyncSession = Depends(get_session)):
    doc = await session.get(Customer, to_uuid(customer_id))
    if not doc:
        raise HTTPException(404, "Klant niet gevonden")
    email = body.email.strip().lower() if body.email else None
    doc.name = body.name
    doc.email = email
    doc.phone = body.phone
    doc.notes = body.notes
    if body.password and not doc.user_id:
        uid = await _create_login(session, email, body.password, body.name, "customer", {"customer_id": doc.id})
        doc.user_id = to_uuid(uid)
    await session.commit()
    return _person_out(CustomerOut, doc)


@router.delete("/customers/{customer_id}")
async def delete_customer(customer_id: str, user: dict = Depends(require_admin),
                          session: AsyncSession = Depends(get_session)):
    cid = to_uuid(customer_id)
    if await session.scalar(select(func.count()).select_from(Event).where(Event.customer_id == cid)):
        raise HTTPException(400, "Deze klant heeft nog events")
    await session.execute(delete(User).where(User.customer_id == cid))
    await session.execute(Customer.__table__.delete().where(Customer.id == cid))
    await session.commit()
    return {"ok": True}


@router.get("/djs")
async def list_djs(user: dict = Depends(require_staff), session: AsyncSession = Depends(get_session)):
    docs = (await session.scalars(select(DJ).order_by(DJ.name.asc()))).all()
    out = []
    for d in docs:
        data = _person_out(DjOut, d)
        data.event_count = await session.scalar(select(func.count()).select_from(Event).where(Event.dj_id == d.id))
        out.append(data)
    return out


@router.post("/djs")
async def create_dj(body: PersonIn, user: dict = Depends(require_admin),
                    session: AsyncSession = Depends(get_session)):
    email = body.email.strip().lower() if body.email else None
    dj = DJ(name=body.name, email=email, phone=body.phone, bio=body.bio, created_at=now())
    session.add(dj)
    await session.flush()
    try:
        uid = await _create_login(session, email, body.password, body.name, "dj", {"dj_id": dj.id})
    except HTTPException:
        await session.rollback()
        raise
    if uid:
        dj.user_id = to_uuid(uid)
    await session.commit()
    return _person_out(DjOut, dj)


@router.patch("/djs/{dj_id}")
async def update_dj(dj_id: str, body: PersonIn, user: dict = Depends(require_admin),
                    session: AsyncSession = Depends(get_session)):
    doc = await session.get(DJ, to_uuid(dj_id))
    if not doc:
        raise HTTPException(404, "DJ niet gevonden")
    email = body.email.strip().lower() if body.email else None
    doc.name = body.name
    doc.email = email
    doc.phone = body.phone
    doc.bio = body.bio
    if body.password and not doc.user_id:
        uid = await _create_login(session, email, body.password, body.name, "dj", {"dj_id": doc.id})
        doc.user_id = to_uuid(uid)
    await session.commit()
    return _person_out(DjOut, doc)


@router.get("/users")
async def list_users(user: dict = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    docs = (await session.scalars(select(User))).all()
    return [UserOut.model_validate(d) for d in docs]


def _days_until(value: Optional[date]) -> Optional[int]:
    if not value:
        return None
    return (value - date.today()).days


@router.get("/admin/overview")
async def overview(user: dict = Depends(require_staff), session: AsyncSession = Depends(get_session)):
    from core import event_scope
    scope = event_scope(user)
    stmt = select(Event)
    if scope is not None:
        stmt = stmt.where(scope)
    docs = (await session.scalars(stmt)).all()
    events = [await enrich_event(session, d, user) for d in docs]
    active = [e for e in events if e.status != "completed"]
    upcoming = sorted([e for e in active if (_days_until(e.date) or -1) >= 0], key=lambda e: e.date)

    attention = []
    for e in active:
        reasons = []
        days = _days_until(e.date)
        if e.unread:
            reasons.append(f"{e.unread} ongelezen bericht(en)")
        if days is not None and 0 <= days <= 90 and e.progress.overall < 60:
            reasons.append(f"Over {days} dagen, pas {e.progress.overall}% klaar")
        if e.status == "new":
            reasons.append("Nog niet opgepakt")
        if not e.dj_id:
            reasons.append("Geen DJ toegewezen")
        if reasons:
            attention.append({**e.model_dump(mode="json"), "reasons": reasons})

    ids = [e.id for e in events]
    titles = {e.id: e.title for e in events}
    unread_docs = (await session.scalars(
        select(Message).where(Message.event_id.in_(ids), unread_filter(user))
        .order_by(Message.created_at.desc()).limit(10))).all() if ids else []
    unread = []
    for m in unread_docs:
        item = MessageOut.model_validate(m).model_dump(mode="json")
        item["event_title"] = titles.get(m.event_id)
        unread.append(item)
    incomplete = [e for e in active if e.stats and e.stats.get("missing_info")]
    recent = sorted(events, key=lambda e: e.updated_at or e.created_at, reverse=True)[:6]

    return {
        "counts": {"upcoming": len(upcoming), "attention": len(attention),
                   "unread": sum(e.unread or 0 for e in events), "incomplete": len(incomplete)},
        "upcoming": upcoming[:6], "attention": attention[:6], "unread_messages": unread,
        "incomplete": incomplete[:6], "recent": recent,
    }
