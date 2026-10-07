import logging
import os
import secrets
from datetime import date, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import hash_password, now, to_uuid
from database import SessionLocal
from models import (Customer, DJ, Event, InvitationTemplate, LoginAttempt, Message, MusicItem,
                    PasswordResetToken, TimelineItem, User)

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


# Demo people are identified by these e-mail addresses (example.nl is never a real customer),
# so the demo set can be removed again without touching real data.
DEMO_DJ_EMAILS = ("bas@example.nl", "thomas@example.nl")
DEMO_CUSTOMER_EMAILS = ("jeroen@example.nl", "sanne@example.nl", "events@example.nl")


def _demo_seed_enabled() -> bool:
    return os.environ.get("SEED_DEMO", "false").strip().lower() in {"1", "true", "yes", "on"}


async def ensure_user(session: AsyncSession, email: str, password: str, name: str, role: str, **link) -> str:
    """Create the user if it does not exist. Never overwrites an existing password."""
    email = email.lower()
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        return str(existing.id)
    user = User(email=email, name=name, role=role, created_at=now(), password_hash=hash_password(password), **link)
    session.add(user)
    await session.flush()
    return str(user.id)


async def ensure_templates(session: AsyncSession):
    """Reference data: the invitation templates every event can use."""
    if not await session.scalar(select(func.count()).select_from(InvitationTemplate)):
        session.add_all([InvitationTemplate(**t, active=True, created_at=now()) for t in TEMPLATES])
        await session.flush()


async def add_person(session: AsyncSession, model, role: str, link_key: str, data: dict, password=None) -> str:
    person = model(**data, created_at=now())
    session.add(person)
    await session.flush()
    pid = str(person.id)
    if password and data.get("email"):
        uid = await ensure_user(session, data["email"], password, data["name"], role, **{link_key: person.id})
        person.user_id = to_uuid(uid)
    return pid


async def cleanup_expired(session: AsyncSession):
    """Drop expired password-reset tokens and stale login-attempt rows."""
    await session.execute(delete(PasswordResetToken).where(PasswordResetToken.expires_at < now()))
    await session.execute(delete(LoginAttempt).where(LoginAttempt.updated_at < now() - timedelta(days=1)))


async def _demo_ids(session: AsyncSession):
    cust = list(await session.scalars(select(Customer.id).where(Customer.email.in_(DEMO_CUSTOMER_EMAILS))))
    djs = list(await session.scalars(select(DJ.id).where(DJ.email.in_(DEMO_DJ_EMAILS))))
    return cust, djs


async def demo_status(session: AsyncSession) -> dict:
    cust, djs = await _demo_ids(session)
    events = await session.scalar(select(func.count()).select_from(Event).where(Event.customer_id.in_(cust))) if cust else 0
    return {"enabled": bool(cust or djs), "events": events or 0, "customers": len(cust), "djs": len(djs)}


async def remove_demo(session: AsyncSession) -> dict:
    """Delete exactly the demo set: demo customers, their events (children cascade), demo DJs and their logins."""
    cust, djs = await _demo_ids(session)
    events = 0
    if cust:
        events = (await session.execute(delete(Event).where(Event.customer_id.in_(cust)))).rowcount
    users = list(await session.scalars(select(User.id).where(
        (User.customer_id.in_(cust or [None])) | (User.dj_id.in_(djs or [None])))))
    if users:
        await session.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id.in_(users)))
        await session.execute(delete(User).where(User.id.in_(users)))
    if cust:
        await session.execute(delete(Customer).where(Customer.id.in_(cust)))
    if djs:  # events of real customers that used a demo DJ fall back to "geen DJ" (FK SET NULL)
        await session.execute(delete(DJ).where(DJ.id.in_(djs)))
    log.info("Demo data removed (%s events)", events)
    return {"events": events, "customers": len(cust), "djs": len(djs)}


async def seed_demo(session: AsyncSession):
    if (await demo_status(session))["enabled"]:
        return
    # Demo logins only work when DEMO_PASSWORD is set (dev/tests); otherwise they get an unknown password.
    pw = os.environ.get("DEMO_PASSWORD") or secrets.token_urlsafe(24)

    bas = await add_person(session, DJ, "dj", "dj_id", {
        "name": "Bas", "email": "bas@example.nl", "phone": "06 00000001",
        "bio": "Bruiloften en feesten met een volle dansvloer. Van Motown tot moderne house."}, pw)
    thomas = await add_person(session, DJ, "dj", "dj_id", {
        "name": "Thomas", "email": "thomas@example.nl", "phone": "06 00000002",
        "bio": "Allround DJ voor bedrijfsfeesten en verjaardagen."}, pw)
    jm = await add_person(session, Customer, "customer", "customer_id", {
        "name": "Jeroen & Mark", "email": "jeroen@example.nl", "phone": "06 00000010"}, pw)
    sanne = await add_person(session, Customer, "customer", "customer_id", {
        "name": "Sanne de Vries", "email": "sanne@example.nl", "phone": "06 00000011"}, pw)
    vandijk = await add_person(session, Customer, "customer", "customer_id", {
        "name": "Van Dijk Techniek", "email": "events@example.nl"})

    t0 = now()
    event = Event(
        title="Jeroen & Mark", event_type="wedding", date=date(2027, 6, 14), start_time="20:00", end_time="01:00",
        venue_name="Landgoed De Wilmersberg", venue_city="De Lutte", venue_notes="Feestavond in de grote zaal.",
        guest_count=140, notes="Avondprogramma na de ceremonie. Graag een mix van feelgood classics en moderne hits.",
        customer_id=jm, dj_id=bas, status="preparing", contact_name="Lisa (ceremoniemeester)",
        contact_phone="06 00000020", cover_image="/images/reception.jpg",
        created_at=t0 - timedelta(days=30), updated_at=t0)
    session.add(event)
    await session.flush()
    ev = event.id

    convo = [
        ("dj", "Hoi Jeroen en Mark! Ik ben Bas, jullie DJ op 14 juni. Wat leuk dat ik jullie avond mag verzorgen.", False),
        ("dj", "Hebben jullie al nagedacht over de openingsdans?", False),
        ("customer", "Ja, we willen graag 'Perfect' van Ed Sheeran.", True),
        ("dj", "Mooie keuze! Zullen we hem om 22:00 inplannen, direct na het diner?", True),
        ("customer", "Top! En kun je later op de avond ook wat ABBA draaien?", False),
    ]
    for i, (role, text, pinned) in enumerate(convo):
        last = i == len(convo) - 1
        session.add(Message(
            event_id=ev, sender_id=jm if role == "customer" else bas,
            sender_name="Jeroen" if role == "customer" else "Bas", sender_role=role, text=text,
            attachment=None, pinned=pinned, read_by_customer=True, read_by_staff=not last,
            created_at=t0 - timedelta(days=5 - i, hours=3)))

    music = [
        ("must_play", "Dancing Queen", "ABBA", None), ("must_play", "Mr. Brightside", "The Killers", None),
        ("must_play", "Uptown Funk", "Mark Ronson ft. Bruno Mars", None), ("must_play", "Zoutelande", "BLØF", None),
        ("dont_play", "Macarena", "Los del Río", None), ("favorite", "Levitating", "Dua Lipa", None),
        ("favorite", "September", "Earth, Wind & Fire", None),
        ("special", "Perfect", "Ed Sheeran", "opening_dance"),
        ("special", "Signed, Sealed, Delivered", "Stevie Wonder", "entrance"),
    ]
    session.add_all([MusicItem(
        event_id=ev, category=c, title=t, artist=a, moment=m, notes=None, source="manual",
        external_ref={}, added_by_role="customer", created_at=t0) for c, t, a, m in music])

    timeline = [
        ("19:30", "Ontvangst gasten", "Welkomstdrankje met lounge muziek", "glass", "confirmed"),
        ("20:00", "Welkomstwoord", "Ceremoniemeester heet iedereen welkom", "mic", "confirmed"),
        ("20:15", "Diner", "Rustige achtergrondmuziek", "utensils", "confirmed"),
        ("22:00", "Openingsdans", "Perfect – Ed Sheeran", "heart", "confirmed"),
        ("22:05", "Feest begint", "Dansvloer open!", "music", "suggested"),
        ("00:00", "Speciaal moment", "Taart aansnijden", "cake", "suggested"),
        ("01:00", "Einde", "Laatste nummer en uitzwaaien", "moon", "suggested"),
    ]
    session.add_all([TimelineItem(
        event_id=ev, time=tm, title=ti, description=d, icon=ic, status=st,
        created_by_role="dj" if st == "confirmed" else "customer", created_at=t0)
        for tm, ti, d, ic, st in timeline])

    session.add_all([
        Event(title="Sanne wordt 40", event_type="birthday", date=date(2026, 11, 21), start_time="21:00",
              end_time="02:00", venue_name="Feestzaal Het Anker", venue_city="Amersfoort", guest_count=90,
              customer_id=sanne, dj_id=thomas, status="new", cover_image="/images/party.jpg",
              created_at=t0 - timedelta(days=4), updated_at=t0 - timedelta(days=2)),
        Event(title="Kerstborrel Van Dijk Techniek", event_type="corporate", date=date(2026, 12, 18),
              start_time="17:00", end_time=None, venue_name=None, venue_city="Utrecht", guest_count=None,
              customer_id=vandijk, dj_id=None, status="new", cover_image="/images/stage.jpg",
              created_at=t0 - timedelta(days=1), updated_at=t0 - timedelta(days=1)),
    ])
    log.info("Demo data seeded")


async def run_seed():
    async with SessionLocal() as session:
        # Bootstrap admin + reference data on every start; both are idempotent.
        await ensure_user(session, os.environ["ADMIN_EMAIL"], os.environ["ADMIN_PASSWORD"],
                          "White Vision", "admin")
        await ensure_templates(session)
        await cleanup_expired(session)
        # Demo customers/events are opt-in and never seeded in production.
        if _demo_seed_enabled():
            await seed_demo(session)
        await session.commit()
