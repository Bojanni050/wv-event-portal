from core import db, oid, unread_filter
from models import Customer, DJ, Event

INFO_FIELDS = {
    "title": "Naam", "event_type": "Type event", "date": "Datum", "start_time": "Starttijd",
    "end_time": "Eindtijd", "venue_name": "Locatie", "venue_city": "Plaats", "guest_count": "Aantal gasten",
    "dj_id": "DJ",
}
FINAL_FIELDS = {"contact_name": "Contactpersoon op de dag", "contact_phone": "Telefoon contactpersoon",
                "setup_notes": "Opbouw & logistiek"}


def _pct(x: float) -> int:
    return round(max(0.0, min(1.0, x)) * 100)


async def event_stats(ev: dict) -> dict:
    eid = str(ev["_id"])
    grouped = await db.music_items.aggregate(
        [{"$match": {"event_id": eid}}, {"$group": {"_id": "$category", "n": {"$sum": 1}}}]).to_list(10)
    music = {g["_id"]: g["n"] for g in grouped}
    timeline = await db.timeline_items.find({"event_id": eid}, {"status": 1}).to_list(500)
    confirmed = sum(1 for t in timeline if t.get("status") == "confirmed")
    invitation = await db.invitations.find_one({"event_id": eid}, {"share_token": 1})
    files = await db.files.count_documents({"event_id": eid, "category": {"$ne": "chat"}})
    last = await db.messages.find_one({"event_id": eid}, sort=[("created_at", -1)])
    pinned = await db.messages.count_documents({"event_id": eid, "pinned": True})

    missing_info = [label for key, label in INFO_FIELDS.items() if not ev.get(key)]
    missing_final = [label for key, label in FINAL_FIELDS.items() if not ev.get(key)]
    music_score = (0.4 * min(music.get("must_play", 0) / 5, 1) + 0.2 * (music.get("dont_play", 0) > 0)
                   + 0.4 * min(music.get("special", 0) / 3, 1))
    n = len(timeline)
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
            "invitation_saved": bool(invitation), "invitation_shared": bool(invitation and invitation.get("share_token")),
            "pinned_count": pinned, "missing_info": missing_info, "missing_final": missing_final,
            "last_message": {"text": last.get("text") or (last.get("attachment") or {}).get("filename", ""),
                             "sender_name": last["sender_name"], "sender_role": last["sender_role"],
                             "created_at": last["created_at"]} if last else None,
        },
    }


async def enrich_event(ev: dict, user: dict) -> dict:
    data = Event.from_mongo(ev).out()
    data.update(await event_stats(ev))
    data["unread"] = await db.messages.count_documents({"event_id": data["id"], **unread_filter(user)})
    customer = await db.customers.find_one({"_id": oid(ev["customer_id"])}) if ev.get("customer_id") else None
    dj = await db.djs.find_one({"_id": oid(ev["dj_id"])}) if ev.get("dj_id") else None
    data["customer"] = Customer.from_mongo(customer).out() if customer else None
    data["dj"] = DJ.from_mongo(dj).out() if dj else None
    return data
