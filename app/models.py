from enum import StrEnum

from ms_core import AbstractModel as Model
from tortoise import fields


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


class Venue(Model):
    id = fields.UUIDField(primary_key=True)

    name = fields.CharField(max_length=255)
    description = fields.TextField()
    sport_types = fields.JSONField(default=list)  # List[SportType]
    status = fields.CharEnumField(VenueStatus, default=VenueStatus.PENDING_APPROVAL)

    owner_id = fields.UUIDField()

    # Location
    address = fields.CharField(max_length=500)
    city = fields.CharField(max_length=100)
    latitude = fields.DecimalField(max_digits=9, decimal_places=6, null=True)
    longitude = fields.DecimalField(max_digits=9, decimal_places=6, null=True)

    # Price
    price_per_hour = fields.DecimalField(max_digits=8, decimal_places=2)
    currency = fields.CharField(max_length=3, default="EUR")

    # Features
    capacity = fields.IntField(default=1)
    is_indoor = fields.BooleanField(default=False)
    has_parking = fields.BooleanField(default=False)
    has_changing_rooms = fields.BooleanField(default=False)
    has_showers = fields.BooleanField(default=False)
    has_equipment_rental = fields.BooleanField(default=False)
    amenities = fields.JSONField(default=list)

    # 0=Mon - 6=Sun
    working_hours = fields.JSONField(default=dict)
    # For example:
    # {
    #   "0": {"open": "08:00", "close": "22:00"},
    #   "6": {"open": "09:00", "close": "18:00"},
    #   "default": {"open": "08:00", "close": "22:00"}
    # }

    # Meta
    rating = fields.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    total_reviews = fields.IntField(default=0)
    total_bookings = fields.IntField(default=0)

    updated_at = fields.DatetimeField(auto_now=True)

    images: fields.ReverseRelation["VenueImage"]
    unavailabilities: fields.ReverseRelation["VenueUnavailability"]

    class Meta:  # type: ignore
        table = "venues"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.city})"

    class PydanticMeta:
        exclude = ["owner__password_hash"]


class VenueImage(Model):
    id = fields.UUIDField(primary_key=True)
    venue = fields.ForeignKeyField(
        "models.Venue", related_name="images", on_delete=fields.CASCADE
    )
    url = fields.CharField(max_length=500)
    is_thumbnail = fields.BooleanField(default=False)
    order = fields.IntField(default=0)

    class Meta:  # type: ignore
        table = "venue_images"
        ordering = ["order"]


class VenueUnavailability(Model):
    """maintenance, personal reasons etc."""

    id = fields.UUIDField(primary_key=True)
    venue = fields.ForeignKeyField(
        "models.Venue", related_name="unavailabilities", on_delete=fields.CASCADE
    )
    start_datetime = fields.DatetimeField()
    end_datetime = fields.DatetimeField()
    reason = fields.CharField(max_length=255, null=True)

    class Meta:  # type: ignore
        table = "venue_unavailabilities"
