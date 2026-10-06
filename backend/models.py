from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from core import BaseDocument, PyObjectId


class User(BaseDocument):
    email: str
    name: str
    role: str
    customer_id: Optional[PyObjectId] = None
    dj_id: Optional[PyObjectId] = None
    created_at: Optional[datetime] = None


class Customer(BaseDocument):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    user_id: Optional[PyObjectId] = None
    external_id: Optional[str] = None
    welcome_sent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class DJ(BaseDocument):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    user_id: Optional[PyObjectId] = None
    created_at: Optional[datetime] = None


class EventFields(BaseModel):
    title: Optional[str] = None
    event_type: Optional[str] = None
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    venue_name: Optional[str] = None
    venue_city: Optional[str] = None
    venue_address: Optional[str] = None
    venue_notes: Optional[str] = None
    guest_count: Optional[int] = None
    notes: Optional[str] = None
    customer_id: Optional[str] = None
    dj_id: Optional[str] = None
    status: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    setup_notes: Optional[str] = None
    cover_image: Optional[str] = None
    external_id: Optional[str] = None


CUSTOMER_EDITABLE = {"title", "guest_count", "notes", "contact_name", "contact_phone", "setup_notes", "venue_notes"}
EVENT_STATUSES = {"new", "preparing", "ready", "completed"}


class EventCreate(EventFields):
    title: str


class Event(BaseDocument):
    title: str
    event_type: str = "wedding"
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    venue_name: Optional[str] = None
    venue_city: Optional[str] = None
    venue_address: Optional[str] = None
    venue_notes: Optional[str] = None
    guest_count: Optional[int] = None
    notes: Optional[str] = None
    customer_id: Optional[PyObjectId] = None
    dj_id: Optional[PyObjectId] = None
    status: str = "new"
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    setup_notes: Optional[str] = None
    cover_image: Optional[str] = None
    external_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Message(BaseDocument):
    event_id: PyObjectId
    sender_id: PyObjectId
    sender_name: str
    sender_role: str
    text: str = ""
    attachment: Optional[dict] = None
    pinned: bool = False
    read_by_customer: bool = False
    read_by_staff: bool = False
    created_at: datetime


class MusicItem(BaseDocument):
    event_id: PyObjectId
    category: str
    moment: Optional[str] = None
    title: str
    artist: Optional[str] = None
    notes: Optional[str] = None
    source: str = "manual"
    external_ref: dict = Field(default_factory=dict)
    added_by_role: str = "customer"
    created_at: Optional[datetime] = None


class TimelineItem(BaseDocument):
    event_id: PyObjectId
    time: str
    title: str
    description: Optional[str] = None
    icon: str = "sparkles"
    status: str = "confirmed"
    created_by_role: str = "admin"
    created_at: Optional[datetime] = None


class FileMeta(BaseDocument):
    event_id: PyObjectId
    filename: str
    content_type: str
    size: int
    category: str = "document"
    gridfs_id: PyObjectId
    uploaded_by: PyObjectId
    uploaded_by_name: str
    uploaded_by_role: str
    created_at: Optional[datetime] = None


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


class Rsvp(BaseDocument):
    event_id: PyObjectId
    name: str
    email: Optional[str] = None
    attending: str
    guests: int = 1
    dietary: Optional[str] = None
    message: Optional[str] = None
    created_at: Optional[datetime] = None


class Invitation(BaseDocument, InvitationFields):
    event_id: PyObjectId
    share_token: Optional[str] = None
    updated_at: Optional[datetime] = None


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


class InvitationTemplate(BaseDocument, TemplateFields):
    created_at: Optional[datetime] = None
