"""Pydantic request/response schemas.

Response schemas mirror the JSON the frontend already consumes (all ids are
strings), so swapping the database does not change the API contract. ORM rows
are validated into these models with ``from_attributes``.
"""
import uuid
import datetime as dt
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

CUSTOMER_EDITABLE = {"title", "guest_count", "notes", "contact_name", "contact_phone", "setup_notes", "venue_notes"}
EVENT_STATUSES = {"new", "preparing", "ready", "completed"}


def _empty_to_none(value):
    """Treat empty strings as ``None`` (forms send "" for optional fields)."""
    if isinstance(value, str) and not value.strip():
        return None
    return value


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- people
class UserOut(ORMModel):
    id: uuid.UUID
    email: str
    name: str
    role: str
    customer_id: Optional[uuid.UUID] = None
    dj_id: Optional[uuid.UUID] = None
    created_at: Optional[dt.datetime] = None


class CustomerOut(ORMModel):
    id: uuid.UUID
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    external_id: Optional[str] = None
    welcome_sent_at: Optional[dt.datetime] = None
    created_at: Optional[dt.datetime] = None
    has_login: Optional[bool] = None
    event_count: Optional[int] = None
    welcome_error: Optional[str] = None


class DjOut(ORMModel):
    id: uuid.UUID
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    created_at: Optional[dt.datetime] = None
    has_login: Optional[bool] = None
    event_count: Optional[int] = None


# --------------------------------------------------------------------------- events
class ProgressSection(BaseModel):
    key: str
    label: str
    percent: int


class Progress(BaseModel):
    overall: int
    sections: list[ProgressSection]


class EventFields(BaseModel):
    title: Optional[str] = None
    event_type: Optional[str] = None
    date: Optional[dt.date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    venue_name: Optional[str] = None
    venue_city: Optional[str] = None
    venue_address: Optional[str] = None
    venue_notes: Optional[str] = None
    guest_count: Optional[int] = None
    notes: Optional[str] = None
    customer_id: Optional[uuid.UUID] = None
    dj_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    setup_notes: Optional[str] = None
    cover_image: Optional[str] = None
    external_id: Optional[str] = None

    @field_validator("date", "guest_count", "customer_id", "dj_id", mode="before")
    @classmethod
    def _coerce_blank(cls, value):
        return _empty_to_none(value)


class EventCreate(EventFields):
    title: str


class EventOut(ORMModel):
    id: uuid.UUID
    title: str
    event_type: str
    date: Optional[dt.date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    venue_name: Optional[str] = None
    venue_city: Optional[str] = None
    venue_address: Optional[str] = None
    venue_notes: Optional[str] = None
    guest_count: Optional[int] = None
    notes: Optional[str] = None
    customer_id: Optional[uuid.UUID] = None
    dj_id: Optional[uuid.UUID] = None
    status: str
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    setup_notes: Optional[str] = None
    cover_image: Optional[str] = None
    external_id: Optional[str] = None
    created_at: Optional[dt.datetime] = None
    updated_at: Optional[dt.datetime] = None
    # Derived fields attached by services.enrich_event
    progress: Optional[Progress] = None
    stats: Optional[dict] = None
    unread: Optional[int] = None
    customer: Optional[CustomerOut] = None
    dj: Optional[DjOut] = None


# --------------------------------------------------------------------------- chat
class MessageAttachment(BaseModel):
    file_id: str
    filename: str
    content_type: str
    size: int


class MessageIn(BaseModel):
    text: str = ""
    attachment_file_id: Optional[str] = None


class PinIn(BaseModel):
    pinned: bool


class MessageOut(ORMModel):
    id: uuid.UUID
    event_id: uuid.UUID
    sender_id: uuid.UUID
    sender_name: str
    sender_role: str
    text: str
    attachment: Optional[MessageAttachment] = None
    pinned: bool
    read_by_customer: bool
    read_by_staff: bool
    created_at: Optional[dt.datetime] = None


# --------------------------------------------------------------------------- music
class MusicIn(BaseModel):
    category: str
    title: str
    artist: Optional[str] = None
    notes: Optional[str] = None
    moment: Optional[str] = None


class MusicUpdate(BaseModel):
    category: Optional[str] = None
    title: Optional[str] = None
    artist: Optional[str] = None
    notes: Optional[str] = None
    moment: Optional[str] = None


class MusicItemOut(ORMModel):
    id: uuid.UUID
    event_id: uuid.UUID
    category: str
    moment: Optional[str] = None
    title: str
    artist: Optional[str] = None
    notes: Optional[str] = None
    source: str
    external_ref: dict = Field(default_factory=dict)
    added_by_role: str
    created_at: Optional[dt.datetime] = None


# --------------------------------------------------------------------------- timeline
class TimelineIn(BaseModel):
    time: str
    title: str
    description: Optional[str] = None
    icon: str = "sparkles"
    status: Optional[str] = None


class TimelineUpdate(BaseModel):
    time: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    status: Optional[str] = None


class TimelineItemOut(ORMModel):
    id: uuid.UUID
    event_id: uuid.UUID
    time: str
    title: str
    description: Optional[str] = None
    icon: str
    status: str
    created_by_role: str
    created_at: Optional[dt.datetime] = None


# --------------------------------------------------------------------------- files
class FileOut(ORMModel):
    id: uuid.UUID
    event_id: uuid.UUID
    filename: str
    content_type: str
    size: int
    category: str
    uploaded_by: uuid.UUID
    uploaded_by_name: str
    uploaded_by_role: str
    created_at: Optional[dt.datetime] = None


# --------------------------------------------------------------------------- invitations
class InvitationFields(BaseModel):
    template_id: Optional[str] = None
    title: str = ""
    subtitle: Optional[str] = None
    date_text: Optional[str] = None
    time_text: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    photo_url: Optional[str] = None
    photo_file_id: Optional[str] = None
    background_color: str = "#09090B"
    text_color: str = "#F4F4F5"
    accent_color: str = "#D4AF37"
    font: str = "playfair"
    layout: str = "classic"
    rsvp_enabled: bool = True
    rsvp_deadline: Optional[str] = None


class InvitationOut(ORMModel):
    id: uuid.UUID
    event_id: Optional[uuid.UUID] = None
    template_id: Optional[str] = None
    title: str
    subtitle: Optional[str] = None
    date_text: Optional[str] = None
    time_text: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    photo_url: Optional[str] = None
    photo_file_id: Optional[str] = None
    background_color: str
    text_color: str
    accent_color: str
    font: str
    layout: str
    rsvp_enabled: bool
    rsvp_deadline: Optional[str] = None
    share_token: Optional[str] = None
    updated_at: Optional[dt.datetime] = None


class TemplateFields(BaseModel):
    name: str
    description: Optional[str] = None
    layout: str = "classic"
    background_color: str = "#09090B"
    text_color: str = "#F4F4F5"
    accent_color: str = "#D4AF37"
    font: str = "playfair"
    subtitle: Optional[str] = None
    photo_url: Optional[str] = None
    active: bool = True


class TemplateOut(ORMModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    layout: str
    background_color: str
    text_color: str
    accent_color: str
    font: str
    subtitle: Optional[str] = None
    photo_url: Optional[str] = None
    active: bool
    created_at: Optional[dt.datetime] = None


# --------------------------------------------------------------------------- rsvp
class RsvpIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: Optional[str] = Field(default=None, max_length=200)
    attending: str
    guests: int = Field(default=1, ge=1, le=20)
    dietary: Optional[str] = Field(default=None, max_length=300)
    message: Optional[str] = Field(default=None, max_length=1000)


class RsvpOut(ORMModel):
    id: uuid.UUID
    event_id: uuid.UUID
    name: str
    email: Optional[str] = None
    attending: str
    guests: int
    dietary: Optional[str] = None
    message: Optional[str] = None
    created_at: Optional[dt.datetime] = None


# --------------------------------------------------------------------------- auth / account / admin input
class LoginIn(BaseModel):
    email: str
    password: str


class PasswordIn(BaseModel):
    current_password: str
    new_password: str


class ForgotIn(BaseModel):
    email: str = Field(max_length=200)


class ResetIn(BaseModel):
    token: str = Field(max_length=200)
    new_password: str = Field(max_length=200)


class AccountIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=200)
    phone: Optional[str] = Field(default=None, max_length=40)


class PersonIn(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    bio: Optional[str] = None
    password: Optional[str] = None
    send_welcome: bool = False
