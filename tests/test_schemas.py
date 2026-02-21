from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import (
    SportType,
    VenueCreate,
    VenueFilters,
    VenueStatus,
    VenueUnavailabilityCreate,
)

from .factories import LATER, NOW


class TestVenueCreateSchema:
    def test_valid_payload(self):
        data = VenueCreate(
            name="Tennis Club",
            description="A wonderful tennis club in the city centre.",
            address="1 Sports Ave",
            city="Sofia",
            price_per_hour=Decimal("25.00"),
            sport_types=[SportType.TENNIS],
        )
        assert data.currency == "EUR"
        assert data.capacity == 1

    def test_currency_uppercased(self):
        data = VenueCreate(
            name="Club",
            description="Long enough description here.",
            address="Addr",
            city="City",
            price_per_hour=Decimal("10"),
            currency="eur",
        )
        assert data.currency == "EUR"

    def test_sport_types_deduplicated(self):
        data = VenueCreate(
            name="Multi-sport",
            description="Long enough description here.",
            address="Addr",
            city="City",
            price_per_hour=Decimal("10"),
            sport_types=[SportType.FOOTBALL, SportType.FOOTBALL, SportType.GYM],
        )
        assert data.sport_types == [SportType.FOOTBALL, SportType.GYM]

    def test_name_too_short_raises(self):
        with pytest.raises(ValidationError):
            VenueCreate(
                name="X",
                description="Fine description.",
                address="Addr",
                city="City",
                price_per_hour=Decimal("10"),
            )

    def test_negative_price_raises(self):
        with pytest.raises(ValidationError):
            VenueCreate(
                name="Club",
                description="Fine description.",
                address="Addr",
                city="City",
                price_per_hour=Decimal("-5"),
            )

    def test_capacity_zero_raises(self):
        with pytest.raises(ValidationError):
            VenueCreate(
                name="Club",
                description="Fine description.",
                address="Addr",
                city="City",
                price_per_hour=Decimal("10"),
                capacity=0,
            )


class TestWorkingHoursSchema:
    def test_valid_working_hours(self):
        data = VenueCreate(
            name="Morning Club",
            description="Opens early every day of the week.",
            address="Addr",
            city="City",
            price_per_hour=Decimal("10"),
            working_hours={
                "default": {"open": "08:00", "close": "22:00"},
                "6": {"open": "10:00", "close": "18:00"},
            },
        )
        assert "default" in data.working_hours
        assert "6" in data.working_hours

    def test_invalid_day_key_raises(self):
        with pytest.raises(Exception, match="invalid day key"):
            VenueCreate(
                name="Morning Club",
                description="Opens early every day of the week.",
                address="Addr",
                city="City",
                price_per_hour=Decimal("10"),
                working_hours={"8": {"open": "08:00", "close": "22:00"}},
            )

    def test_close_before_open_raises(self):
        with pytest.raises(ValidationError):
            VenueCreate(
                name="Morning Club",
                description="Opens early every day of the week.",
                address="Addr",
                city="City",
                price_per_hour=Decimal("10"),
                working_hours={"0": {"open": "22:00", "close": "08:00"}},
            )


class TestVenueFiltersSchema:
    def test_price_range_inversion_raises(self):
        with pytest.raises(Exception, match="min_price"):
            VenueFilters(min_price=Decimal("100"), max_price=Decimal("10"))

    def test_defaults(self):
        f = VenueFilters()
        assert f.page == 1
        assert f.page_size == 20
        assert f.status == VenueStatus.ACTIVE

    def test_page_size_capped(self):
        with pytest.raises(ValidationError):
            VenueFilters(page_size=999)


class TestUnavailabilitySchema:
    def test_end_before_start_raises(self):
        with pytest.raises(Exception, match="end_datetime"):
            VenueUnavailabilityCreate(
                start_datetime=LATER,
                end_datetime=NOW,
            )

    def test_valid_window(self):
        obj = VenueUnavailabilityCreate(
            start_datetime=NOW,
            end_datetime=LATER,
            reason="Holiday",
        )
        assert obj.reason == "Holiday"
