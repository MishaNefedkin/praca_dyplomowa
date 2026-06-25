from datetime import datetime
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


InquiryStatus = Literal["new", "in_progress", "offer_sent", "closed"]
OfferStatus = Literal["draft", "sent", "accepted", "rejected"]
UserRole = Literal["admin", "sales", "manager"]
PHONE_PATTERN = re.compile(r"^[0-9+()\s-]+$")
MIN_PHONE_DIGITS = 6


def validate_phone_number(phone: str | None) -> str | None:
    if phone is None:
        return None
    normalized = phone.strip()
    if not normalized:
        return None
    if not PHONE_PATTERN.fullmatch(normalized):
        raise ValueError("Phone number can contain only digits, spaces, +, -, and parentheses")
    if sum(character.isdigit() for character in normalized) < MIN_PHONE_DIGITS:
        raise ValueError("Phone number must contain at least 6 digits")
    return normalized


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    login: str
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    role: UserRole
    created_at: datetime


class UserCreate(BaseModel):
    login: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=120)
    role: UserRole = "sales"


class UserUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=8, max_length=120)
    role: UserRole | None = None


class ClientBase(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=60)
    session_id: str | None = Field(default=None, max_length=120)

    @field_validator("phone")
    @classmethod
    def phone_contains_only_phone_characters(cls, value: str | None) -> str | None:
        return validate_phone_number(value)


class ClientCreate(ClientBase):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr


class ClientUpdate(ClientBase):
    pass


class ClientRead(ClientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class InquiryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=60)
    message: str = Field(min_length=5)
    session_id: str = Field(min_length=8, max_length=120)
    consent_granted: Literal[True]
    consent_scope: Literal["contact_and_analytics"] = "contact_and_analytics"

    @field_validator("phone")
    @classmethod
    def phone_contains_only_phone_characters(cls, value: str | None) -> str | None:
        return validate_phone_number(value)


class InquiryAdminCreate(BaseModel):
    client_id: int
    message: str = Field(min_length=5)
    status: InquiryStatus = "new"


class InquiryUpdate(BaseModel):
    status: InquiryStatus | None = None
    message: str | None = Field(default=None, min_length=5)


class InquiryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    status: InquiryStatus
    message: str
    created_at: datetime


class OfferCreate(BaseModel):
    inquiry_id: int
    value: float = Field(ge=0)
    status: OfferStatus = "draft"
    deadline: datetime | None = None


class OfferUpdate(BaseModel):
    value: float | None = Field(default=None, ge=0)
    status: OfferStatus | None = None
    deadline: datetime | None = None


class OfferRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    inquiry_id: int
    value: float
    status: OfferStatus
    deadline: datetime | None
    created_at: datetime


class TrackingEventCreate(BaseModel):
    session_id: str = Field(min_length=8, max_length=120)
    page_url: str = Field(min_length=1, max_length=500)
    event_type: Literal["page_view", "page_leave", "cta_click", "form_interaction", "form_submit"]
    event_data: dict[str, Any] | None = None
    referrer: str | None = Field(default=None, max_length=500)
    time_on_page: int | None = Field(default=None, ge=0)

    @field_validator("event_data")
    @classmethod
    def limit_event_data(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None and len(json.dumps(value)) > 2000:
            raise ValueError("event_data is too large")
        return value


class ActivityLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    client_id: int | None
    page_url: str
    event_type: str
    event_data: dict[str, Any] | None
    referrer: str | None
    time_on_page: int | None
    logged_at: datetime


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_user_id: int | None
    actor_login: str
    action: str
    entity_type: str
    entity_id: int | None
    details: dict[str, Any] | None
    created_at: datetime


class ConsentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    scope: str
    granted_at: datetime
    active: bool


class ConsentUpdate(BaseModel):
    active: bool


class KPIRead(BaseModel):
    clients_count: int
    new_inquiries_count: int
    sent_offers_count: int
    inquiry_to_offer_conversion_rate: float
    activities_last_24h: int


class TopPageRead(BaseModel):
    page_url: str
    visits: int


class TimelineItem(BaseModel):
    type: str
    title: str
    timestamp: datetime
    data: dict[str, Any]
