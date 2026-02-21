from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)


class SportType(StrEnum):
    FOOTBALL = "football"
    BASKETBALL = "basketball"
    TENNIS = "tennis"
    VOLLEYBALL = "volleyball"
    SWIMMING = "swimming"
    GYM = "gym"
    PADEL = "padel"
    OTHER = "other"


class VenueStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    PENDING_APPROVAL = "pending_approval"


class DayHours(BaseModel):
    """Opening and closing time for a single day."""

    open: time
    close: time

    @model_validator(mode="after")
    def close_after_open(self) -> DayHours:
        if self.close <= self.open:
            raise ValueError("close time must be after open time")
        return self

    @field_serializer("open", "close")
    def serialize_time(self, t: time):
        return t.strftime("%H:%M")


WeeklyHours = dict[str, DayHours]


def _validate_working_hours(value: Any) -> WeeklyHours:
    """Coerce raw dict → WeeklyHours and validate day keys."""
    if not isinstance(value, dict):
        raise ValueError("working_hours must be a dict")
    allowed_keys = {str(i) for i in range(7)} | {"default"}
    result: WeeklyHours = {}
    for k, v in value.items():
        if k not in allowed_keys:
            raise ValueError(f"invalid day key '{k}'; must be '0'–'6' or 'default'")
        result[k] = DayHours.model_validate(v)
    return result


class VenueImageBase(BaseModel):
    url: str = Field(..., max_length=500)
    is_thumbnail: bool = False
    order: int = Field(default=0, ge=0)


class VenueImageCreate(VenueImageBase):
    """Used when adding an image to a venue (venue_id comes from the path)."""

    pass


class VenueImageUpdate(BaseModel):
    """Partial update — all fields optional."""

    url: str | None = Field(default=None, max_length=500)
    is_thumbnail: bool | None = None
    order: int | None = Field(default=None, ge=0)


class VenueImageResponse(VenueImageBase):
    id: UUID
    venue_id: UUID

    model_config = ConfigDict(from_attributes=True)


class VenueUnavailabilityBase(BaseModel):
    start_datetime: datetime
    end_datetime: datetime
    reason: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def end_after_start(self) -> VenueUnavailabilityBase:
        if self.end_datetime <= self.start_datetime:
            raise ValueError("end_datetime must be after start_datetime")
        return self


class VenueUnavailabilityCreate(VenueUnavailabilityBase):
    """Used when blocking time for a venue (venue_id comes from the path)."""

    pass


class VenueUnavailabilityUpdate(BaseModel):
    """Partial update — all fields optional."""

    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    reason: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def end_after_start(self) -> VenueUnavailabilityUpdate:
        if (
            self.start_datetime
            and self.end_datetime
            and (self.end_datetime <= self.start_datetime)
        ):
            raise ValueError("end_datetime must be after start_datetime")
        return self


class VenueUnavailabilityResponse(VenueUnavailabilityBase):
    id: UUID
    venue_id: UUID

    model_config = ConfigDict(from_attributes=True)


class VenueBase(BaseModel):
    # Core
    name: str = Field(..., min_length=2, max_length=255)
    description: str = Field(..., min_length=10)
    sport_types: list[SportType] = Field(default_factory=list)

    # Location
    address: str = Field(..., max_length=500)
    city: str = Field(..., max_length=100)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, decimal_places=6)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, decimal_places=6)

    # Price
    price_per_hour: Decimal = Field(..., ge=0, decimal_places=2)
    currency: Annotated[str, Field(min_length=3, max_length=3)] = "EUR"

    # Features
    capacity: int = Field(default=1, ge=1)
    is_indoor: bool = False
    has_parking: bool = False
    has_changing_rooms: bool = False
    has_showers: bool = False
    has_equipment_rental: bool = False
    amenities: list[str] = Field(default_factory=list)

    # Schedule
    working_hours: WeeklyHours = Field(default_factory=dict)

    @field_validator("sport_types", mode="before")
    @classmethod
    def deduplicate_sport_types(cls, v: Any) -> Any:
        if isinstance(v, list):
            seen: list[Any] = []
            for item in v:
                if item not in seen:
                    seen.append(item)
            return seen
        return v

    @field_validator("currency", mode="before")
    @classmethod
    def uppercase_currency(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.upper()
        return v

    @field_validator("working_hours", mode="before")
    @classmethod
    def validate_working_hours(cls, v: Any) -> Any:
        if not v:
            return {}
        return _validate_working_hours(v)


class VenueCreate(VenueBase):
    """
    Payload for POST /venues.
    owner_id is injected from the authenticated user — not accepted from the client.
    Status starts as PENDING_APPROVAL by default.
    """

    pass


class VenueUpdate(BaseModel):
    """
    Partial update for PATCH /venues/{id}.
    Every field is optional; only provided fields are applied.
    """

    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, min_length=10)
    sport_types: list[SportType] | None = None

    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)

    price_per_hour: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)

    capacity: int | None = Field(default=None, ge=1)
    is_indoor: bool | None = None
    has_parking: bool | None = None
    has_changing_rooms: bool | None = None
    has_showers: bool | None = None
    has_equipment_rental: bool | None = None
    amenities: list[str] | None = None

    working_hours: WeeklyHours | None = None

    @field_validator("currency", mode="before")
    @classmethod
    def uppercase_currency(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.upper()
        return v

    @field_validator("working_hours", mode="before")
    @classmethod
    def validate_working_hours(cls, v: Any) -> Any:
        if v is None:
            return None
        return _validate_working_hours(v)


class VenueStatusUpdate(BaseModel):
    """Used by admins for PATCH /venues/{id}/status."""

    status: VenueStatus


class VenueResponse(VenueBase):
    """Full venue representation returned from any read endpoint."""

    id: UUID
    owner_id: UUID
    status: VenueStatus

    # Computed / aggregate fields
    rating: Decimal
    total_reviews: int
    total_bookings: int

    updated_at: datetime

    # Related
    images: list[VenueImageResponse] = Field(default_factory=list)
    unavailabilities: list[VenueUnavailabilityResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class VenueListItem(BaseModel):
    """
    Lightweight projection for GET /venues (list / search).
    Omits heavy relations and bulk fields.
    """

    id: UUID
    name: str
    city: str
    sport_types: list[SportType]
    status: VenueStatus
    price_per_hour: Decimal
    currency: str
    capacity: int
    is_indoor: bool
    rating: Decimal
    total_reviews: int
    thumbnail: str | None = None  # first image with is_thumbnail=True if any

    model_config = ConfigDict(from_attributes=True)


class VenueFilters(BaseModel):
    """Bind to a FastAPI route via Depends(VenueFilters)."""

    city: str | None = None
    sport_type: SportType | None = None
    is_indoor: bool | None = None
    has_parking: bool | None = None
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    min_capacity: int | None = Field(default=None, ge=1)
    status: VenueStatus | None = VenueStatus.ACTIVE
    owner_id: UUID | None = None

    # Pagination
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def price_range_sane(self) -> VenueFilters:
        if (
            self.min_price is not None
            and self.max_price is not None
            and (self.min_price > self.max_price)
        ):
            raise ValueError("min_price must be ≤ max_price")
        return self
