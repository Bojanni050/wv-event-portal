"""Derived data: event progress, per-section completion and enrichment.

PostgreSQL port of the old aggregation pipelines (``$group`` -> ``GROUP BY``).
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import unread_filter
from models import Customer, DJ, Event, FileMeta, Invitation, Message, MusicItem, Rsvp, TimelineItem
from schemas import CustomerOut, DjOut, EventOut, Progress, ProgressSection

INFO_FIELDS = {
    "title": "Naam", "event_type": "Type event", "date": "Datum", "start_time": "Starttijd",
    "end_time": "Eindtijd", "venue_name": "Locatie", "venue_city": "Plaats", "guest_count": "Aantal gasten",
    "dj_id": "DJ",
}
FINAL_FIELDS = {"contact_name": "Contactpersoon op de dag", "contact_phone": "Telefoon contactpersoon",
                "setup_notes": "Opbouw & logistiek"}


def _pct(x: float) -> int:
    return round(max(0.0, min(1.0, x)) * 100)


async def event_stats(session: AsyncSession, ev: Event) -> dict:
    eid = ev.id

    grouped = await session.execute(
        select(MusicItem.category, func.count()).where(MusicItem.event_id == eid).group_by(MusicItem.category))
    music = {category: count for category, count in grouped.all()}

    timeline = (await session.scalars(select(TimelineItem).where(TimelineItem.event_id == eid))).all()
    confirmed = sum(1 for t in timeline if t.status == "confirmed")
    n = len(timeline)

    invitation = await session.scalar(select(Invitation).where(Invitation.event_id == eid))
    files = await session.scalar(select(func.count()).select_from(FileMeta)
                                 .where(FileMeta.event_id == eid, FileMeta.category != "chat"))
    last = await session.scalar(select(Message).where(Message.event_id == eid)
                                .order_by(Message.created_at.desc()).limit(1))
    pinned = await session.scalar(select(func.count()).select_from(Message)
                                  .where(Message.event_id == eid, Message.pinned.is_(True)))

    rsvp_rows = await session.execute(
        select(Rsvp.attending, func.count(), func.coalesce(func.sum(Rsvp.guests), 0))
        .where(Rsvp.event_id == eid).group_by(Rsvp.attending))
    rsvp = {att: {"n": count, "guests": int(guests or 0)} for att, count, guests in rsvp_rows.all()}

    # ``dj_id`` is a UUID column; the completeness check just cares whether it is set.
    raw = {c.name: getattr(ev, c.name) for c in ev.__table__.columns}
    missing_info = [label for key, label in INFO_FIELDS.items() if not raw.get(key)]
    missing_final = [label for key, label in FINAL_FIELDS.items() if not raw.get(key)]

    music_score = (0.4 * min(music.get("must_play", 0) / 5, 1) + 0.2 * (music.get("dont_play", 0) > 0)
                   + 0.4 * min(music.get("special", 0) / 3, 1))
    timeline_score = 0.5 * min(n / 6, 1) + 0.5 * (confirmed / n) if n else 0

    sections = [
        {"key": "info", "label": "Eventinformatie", "percent": _pct(1 - len(missing_info) / len(INFO_FIELDS))},
        {"key": "music", "label": "Muziekvoorkeuren", "percent": _pct(music_score)},
        {"key": "timeline", "label": "Draaischema", "percent": _pct(timeline_score)},
        {"key": "invitation", "label": "Uitnodiging", "percent": 100 if invitation else 0},
        {"key": "final", "label": "Laatste details", "percent": _pct(1 - len(missing_final) / len(FINAL_FIELDS))},
    ]
    return {
        "progress": {"overall": round(sum(s["percent"] for s in sections) / len(sections)), "sections": sections},
        "stats": {
            "music": {k: music.get(k, 0) for k in ("must_play", "dont_play", "favorite", "special")},
            "timeline_count": n, "timeline_confirmed": confirmed, "files_count": files,
            "invitation_saved": bool(invitation), "invitation_shared": bool(invitation and invitation.share_token),
            "pinned_count": pinned,
            "rsvp": {"responses": sum(r["n"] for r in rsvp.values()),
                     "attending_guests": rsvp.get("yes", {}).get("guests", 0),
                     "declined": rsvp.get("no", {}).get("n", 0), "maybe": rsvp.get("maybe", {}).get("n", 0)},
            "missing_info": missing_info, "missing_final": missing_final,
            "last_message": {"text": (last.text or (last.attachment or {}).get("filename", "")) if last else "",
                             "sender_name": last.sender_name, "sender_role": last.sender_role,
                             "created_at": last.created_at} if last else None,
        },
    }


async def enrich_event(session: AsyncSession, ev: Event, user: dict) -> EventOut:
    stats = await event_stats(session, ev)
    customer = await session.get(Customer, ev.customer_id) if ev.customer_id else None
    dj = await session.get(DJ, ev.dj_id) if ev.dj_id else None
    unread = await session.scalar(select(func.count()).select_from(Message)
                                  .where(Message.event_id == ev.id, unread_filter(user)))

    out = EventOut.model_validate(ev)
    out.progress = Progress(**stats["progress"])
    out.stats = stats["stats"]
    out.unread = unread
    out.customer = CustomerOut.model_validate(customer) if customer else None
    out.dj = DjOut.model_validate(dj) if dj else None
    return out
