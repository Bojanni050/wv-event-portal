import logging
import os
from datetime import timedelta

from core import db, hash_password, now, verify_password

log = logging.getLogger("seed")

TEMPLATES = [
    {"name": "Goud & Nachtclub", "description": "Diep zwart met metallic goud. Tijdloos en feestelijk.",
     "layout": "classic", "background_color": "#09090B", "text_color": "#F4F4F5", "accent_color": "#D4AF37",
     "font": "playfair", "subtitle": "Let's celebrate!", "photo_url": "/images/login.jpg"},
    {"name": "Strak Dutch Minimal", "description": "Zwart op wit, grote typografie, veel lucht.",
     "layout": "minimal", "background_color": "#FAFAFA", "text_color": "#09090B", "accent_color": "#52525B",
     "font": "jakarta", "subtitle": "Save the date", "photo_url": None},
    {"name": "Bohemian Sunset", "description": "Warm terracotta met een romantische serif.",
     "layout": "split", "background_color": "#2A1E1A", "text_color": "#F3E8EE", "accent_color": "#E5C158",
     "font": "cormorant", "subtitle": "Vier het met ons", "photo_url": "/images/venue.jpg"},
    {"name": "Festival Neon", "description": "Energiek en elektrisch, voor een echte party.",
     "layout": "poster", "background_color": "#0F0B1E", "text_color": "#FFFFFF", "accent_color": "#00F0FF",
     "font": "syne", "subtitle": "Tonight we dance", "photo_url": "/images/party.jpg"},
    {"name": "Klassiek Romantisch", "description": "Ivoor en brons, fijn en elegant.",
     "layout": "classic", "background_color": "#FDFBF7", "text_color": "#1C1917", "accent_color": "#B45309",
     "font": "italiana", "subtitle": "Wij gaan trouwen", "photo_url": "/images/romantic.jpg"},
]


async def ensure_user(email: str, password: str, name: str, role: str, **link) -> str:
    email = email.lower()
    existing = await db.users.find_one({"email": email})
    if existing is None:
        res = await db.users.insert_one({"email": email, "name": name, "role": role, "created_at": now(),
                                         "password_hash": hash_password(password), **link})
        return str(res.inserted_id)
    if not verify_password(password, existing["password_hash"]):
        await db.users.update_one({"_id": existing["_id"]}, {"$set": {"password_hash": hash_password(password)}})
    return str(existing["_id"])


async def create_indexes():
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.password_reset_tokens.create_index("token_hash", unique=True)
    await db.customers.create_index("external_id", sparse=True)
    await db.events.create_index("external_id", sparse=True)
    await db.events.create_index([("customer_id", 1), ("date", 1)])
    await db.events.create_index("dj_id")
    await db.messages.create_index([("event_id", 1), ("created_at", 1)])
    for col in ("music_items", "timeline_items", "files", "rsvps"):
        await db[col].create_index("event_id")
    await db.invitations.create_index("event_id", unique=True)
    await db.invitations.create_index("share_token", sparse=True)


async def add_person(collection: str, role: str, link_key: str, data: dict, password=None) -> str:
    res = await db[collection].insert_one({**data, "created_at": now()})
    pid = str(res.inserted_id)
    if password and data.get("email"):
        uid = await ensure_user(data["email"], password, data["name"], role, **{link_key: pid})
        await db[collection].update_one({"_id": res.inserted_id}, {"$set": {"user_id": uid}})
    return pid


async def seed_demo():
    pw = os.environ["DEMO_PASSWORD"]
    if not await db.invitation_templates.count_documents({}):
        await db.invitation_templates.insert_many([{**t, "active": True, "created_at": now()} for t in TEMPLATES])
    if await db.events.count_documents({}):
        return

    bas = await add_person("djs", "dj", "dj_id", {
        "name": "Bas", "email": "bas@white-vision.nl", "phone": "06 00000001",
        "bio": "Bruiloften en feesten met een volle dansvloer. Van Motown tot moderne house."}, pw)
    thomas = await add_person("djs", "dj", "dj_id", {
        "name": "Thomas", "email": "thomas@white-vision.nl", "phone": "06 00000002",
        "bio": "Allround DJ voor bedrijfsfeesten en verjaardagen."}, pw)
    jm = await add_person("customers", "customer", "customer_id", {
        "name": "Jeroen & Mark", "email": "jeroen@example.nl", "phone": "06 00000010"}, pw)
    sanne = await add_person("customers", "customer", "customer_id", {
        "name": "Sanne de Vries", "email": "sanne@example.nl", "phone": "06 00000011"}, pw)
    vandijk = await add_person("customers", "customer", "customer_id", {
        "name": "Van Dijk Techniek", "email": "events@example.nl"})

    t0 = now()
    res = await db.events.insert_one({
        "title": "Jeroen & Mark", "event_type": "wedding", "date": "2027-06-14", "start_time": "20:00",
        "end_time": "01:00", "venue_name": "Landgoed De Wilmersberg", "venue_city": "De Lutte",
        "venue_address": None, "venue_notes": "Feestavond in de grote zaal.", "guest_count": 140,
        "notes": "Avondprogramma na de ceremonie. Graag een mix van feelgood classics en moderne hits.",
        "customer_id": jm, "dj_id": bas, "status": "preparing", "contact_name": "Lisa (ceremoniemeester)",
        "contact_phone": "06 00000020", "setup_notes": None, "cover_image": "/images/reception.jpg",
        "created_at": t0 - timedelta(days=30), "updated_at": t0})
    ev = str(res.inserted_id)

    convo = [
        ("dj", "Hoi Jeroen en Mark! Ik ben Bas, jullie DJ op 14 juni. Wat leuk dat ik jullie avond mag verzorgen.", False),
        ("dj", "Hebben jullie al nagedacht over de openingsdans?", False),
        ("customer", "Ja, we willen graag 'Perfect' van Ed Sheeran.", True),
        ("dj", "Mooie keuze! Zullen we hem om 22:00 inplannen, direct na het diner?", True),
        ("customer", "Top! En kun je later op de avond ook wat ABBA draaien?", False),
    ]
    for i, (role, text, pinned) in enumerate(convo):
        last = i == len(convo) - 1
        await db.messages.insert_one({
            "event_id": ev, "sender_id": jm if role == "customer" else bas,
            "sender_name": "Jeroen" if role == "customer" else "Bas", "sender_role": role, "text": text,
            "attachment": None, "pinned": pinned, "read_by_customer": True, "read_by_staff": not last,
            "created_at": t0 - timedelta(days=5 - i, hours=3)})

    music = [
        ("must_play", "Dancing Queen", "ABBA", None), ("must_play", "Mr. Brightside", "The Killers", None),
        ("must_play", "Uptown Funk", "Mark Ronson ft. Bruno Mars", None), ("must_play", "Zoutelande", "BLØF", None),
        ("dont_play", "Macarena", "Los del Río", None), ("favorite", "Levitating", "Dua Lipa", None),
        ("favorite", "September", "Earth, Wind & Fire", None),
        ("special", "Perfect", "Ed Sheeran", "opening_dance"),
        ("special", "Signed, Sealed, Delivered", "Stevie Wonder", "entrance"),
    ]
    await db.music_items.insert_many([{
        "event_id": ev, "category": c, "title": t, "artist": a, "moment": m, "notes": None, "source": "manual",
        "external_ref": {}, "added_by_role": "customer", "created_at": t0} for c, t, a, m in music])

    timeline = [
        ("19:30", "Ontvangst gasten", "Welkomstdrankje met lounge muziek", "glass", "confirmed"),
        ("20:00", "Welkomstwoord", "Ceremoniemeester heet iedereen welkom", "mic", "confirmed"),
        ("20:15", "Diner", "Rustige achtergrondmuziek", "utensils", "confirmed"),
        ("22:00", "Openingsdans", "Perfect – Ed Sheeran", "heart", "confirmed"),
        ("22:05", "Feest begint", "Dansvloer open!", "music", "suggested"),
        ("00:00", "Speciaal moment", "Taart aansnijden", "cake", "suggested"),
        ("01:00", "Einde", "Laatste nummer en uitzwaaien", "moon", "suggested"),
    ]
    await db.timeline_items.insert_many([{
        "event_id": ev, "time": tm, "title": ti, "description": d, "icon": ic, "status": st,
        "created_by_role": "dj" if st == "confirmed" else "customer", "created_at": t0}
        for tm, ti, d, ic, st in timeline])

    await db.events.insert_many([
        {"title": "Sanne wordt 40", "event_type": "birthday", "date": "2026-11-21", "start_time": "21:00",
         "end_time": "02:00", "venue_name": "Feestzaal Het Anker", "venue_city": "Amersfoort", "guest_count": 90,
         "customer_id": sanne, "dj_id": thomas, "status": "new", "cover_image": "/images/party.jpg",
         "created_at": t0 - timedelta(days=4), "updated_at": t0 - timedelta(days=2)},
        {"title": "Kerstborrel Van Dijk Techniek", "event_type": "corporate", "date": "2026-12-18",
         "start_time": "17:00", "end_time": None, "venue_name": None, "venue_city": "Utrecht", "guest_count": None,
         "customer_id": vandijk, "dj_id": None, "status": "new", "cover_image": "/images/stage.jpg",
         "created_at": t0 - timedelta(days=1), "updated_at": t0 - timedelta(days=1)},
    ])
    log.info("Demo data seeded")


async def run_seed():
    await create_indexes()
    await ensure_user(os.environ["ADMIN_EMAIL"], os.environ["ADMIN_PASSWORD"], "White Vision", "admin")
    await seed_demo()
