"""SQLAlchemy ORM models — one table per domain entity (PostgreSQL).

Replaces the previous Mongo/Pydantic ``BaseDocument`` models. Primary keys are
UUIDs (serialized as strings in JSON so the API contract is unchanged). Child
rows cascade-delete with their event; file contents are stored as ``BYTEA``.

Domain constants (``STAFF_ROLES`` etc.) live in :mod:`core` and :mod:`schemas`.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base, utcnow


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Soft links to the customer/DJ profile (no FK, to avoid a circular constraint).
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), index=True)
    dj_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(64))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True))
    external_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    welcome_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DJ(Base):
    __tablename__ = "djs"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(64))
    bio: Mapped[Optional[str]] = mapped_column(Text)
    photo_url: Mapped[Optional[str]] = mapped_column(Text)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_customer_id_date", "customer_id", "date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), default="wedding", nullable=False)
    date: Mapped[Optional[Date]] = mapped_column(Date)
    start_time: Mapped[Optional[str]] = mapped_column(String(16))
    end_time: Mapped[Optional[str]] = mapped_column(String(16))
    venue_name: Mapped[Optional[str]] = mapped_column(Text)
    venue_city: Mapped[Optional[str]] = mapped_column(Text)
    venue_address: Mapped[Optional[str]] = mapped_column(Text)
    venue_notes: Mapped[Optional[str]] = mapped_column(Text)
    guest_count: Mapped[Optional[int]] = mapped_column(Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), index=True)
    dj_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("djs.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="new", nullable=False)
    contact_name: Mapped[Optional[str]] = mapped_column(Text)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(64))
    setup_notes: Mapped[Optional[str]] = mapped_column(Text)
    cover_image: Mapped[Optional[str]] = mapped_column(Text)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_event_id_created_at", "event_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    sender_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    sender_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_role: Mapped[str] = mapped_column(String(32), nullable=False)
    text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    attachment: Mapped[Optional[dict]] = mapped_column(JSONB)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_by_customer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_by_staff: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MusicItem(Base):
    __tablename__ = "music_items"
    __table_args__ = (Index("ix_music_items_event_id", "event_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    moment: Mapped[Optional[str]] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    artist: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    external_ref: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False, server_default=text("'{}'::jsonb"))
    added_by_role: Mapped[str] = mapped_column(String(32), default="customer", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TimelineItem(Base):
    __tablename__ = "timeline_items"
    __table_args__ = (Index("ix_timeline_items_event_id", "event_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    time: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    icon: Mapped[str] = mapped_column(String(32), default="sparkles", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="confirmed", nullable=False)
    created_by_role: Mapped[str] = mapped_column(String(32), default="admin", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FileMeta(Base):
    __tablename__ = "files"
    __table_args__ = (Index("ix_files_event_id", "event_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(32), default="document", nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    uploaded_by_name: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_by_role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), unique=True, nullable=False)
    template_id: Mapped[Optional[str]] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(Text, default="", nullable=False)
    subtitle: Mapped[Optional[str]] = mapped_column(Text)
    date_text: Mapped[Optional[str]] = mapped_column(Text)
    time_text: Mapped[Optional[str]] = mapped_column(Text)
    location: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    photo_url: Mapped[Optional[str]] = mapped_column(Text)
    photo_file_id: Mapped[Optional[str]] = mapped_column(String(64))
    background_color: Mapped[str] = mapped_column(String(16), default="#09090B", nullable=False)
    text_color: Mapped[str] = mapped_column(String(16), default="#F4F4F5", nullable=False)
    accent_color: Mapped[str] = mapped_column(String(16), default="#D4AF37", nullable=False)
    font: Mapped[str] = mapped_column(String(32), default="playfair", nullable=False)
    layout: Mapped[str] = mapped_column(String(32), default="classic", nullable=False)
    rsvp_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rsvp_deadline: Mapped[Optional[str]] = mapped_column(String(64))
    share_token: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class InvitationTemplate(Base):
    __tablename__ = "invitation_templates"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    layout: Mapped[str] = mapped_column(String(32), default="classic", nullable=False)
    background_color: Mapped[str] = mapped_column(String(16), default="#09090B", nullable=False)
    text_color: Mapped[str] = mapped_column(String(16), default="#F4F4F5", nullable=False)
    accent_color: Mapped[str] = mapped_column(String(16), default="#D4AF37", nullable=False)
    font: Mapped[str] = mapped_column(String(32), default="playfair", nullable=False)
    subtitle: Mapped[Optional[str]] = mapped_column(Text)
    photo_url: Mapped[Optional[str]] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Rsvp(Base):
    __tablename__ = "rsvps"
    __table_args__ = (Index("ix_rsvps_event_id", "event_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    attending: Mapped[str] = mapped_column(String(16), nullable=False)
    guests: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    dietary: Mapped[Optional[str]] = mapped_column(Text)
    message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identifier: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), default="reset", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
