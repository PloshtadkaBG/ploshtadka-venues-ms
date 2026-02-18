from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from ms_core import CRUD
from tortoise.exceptions import DoesNotExist

from app.deps import CurrentUser
from app.scopes import VenueScope

from .models import Venue, VenueImage, VenueUnavailability
from .schemas import (
    VenueCreate,
    VenueFilters,
    VenueImageCreate,
    VenueImageResponse,
    VenueImageUpdate,
    VenueListItem,
    VenueResponse,
    VenueStatus,
    VenueStatusUpdate,
    VenueUnavailabilityCreate,
    VenueUnavailabilityResponse,
    VenueUnavailabilityUpdate,
    VenueUpdate,
)


class VenueImageCRUD(CRUD[VenueImage, VenueImageResponse]):  # type: ignore
    async def create_for_venue(
        self, venue_id: UUID, payload: VenueImageCreate
    ) -> VenueImageResponse:
        # If this is marked as thumbnail, demote any existing thumbnails first.
        if payload.is_thumbnail:
            await VenueImage.filter(venue_id=venue_id, is_thumbnail=True).update(
                is_thumbnail=False
            )

        inst = await VenueImage.create(
            venue_id=venue_id,
            **payload.model_dump(),
        )
        return VenueImageResponse.model_validate(inst, from_attributes=True)

    async def update(
        self, image_id: UUID, venue_id: UUID, payload: VenueImageUpdate
    ) -> VenueImageResponse | None:
        inst = await VenueImage.get_or_none(id=image_id, venue_id=venue_id)
        if not inst:
            return None

        updates = payload.model_dump(exclude_none=True)

        if updates.get("is_thumbnail"):
            await VenueImage.filter(venue_id=venue_id, is_thumbnail=True).update(
                is_thumbnail=False
            )

        await inst.update_from_dict(updates).save()
        return VenueImageResponse.model_validate(inst, from_attributes=True)

    async def delete(self, image_id: UUID, venue_id: UUID) -> bool:
        return await self.delete_by(id=image_id, venue_id=venue_id)

    async def list_for_venue(self, venue_id: UUID) -> list[VenueImageResponse]:
        images = await VenueImage.filter(venue_id=venue_id).order_by("order")
        return [
            VenueImageResponse.model_validate(img, from_attributes=True)
            for img in images
        ]

    async def reorder(
        self, venue_id: UUID, ordered_ids: list[UUID]
    ) -> list[VenueImageResponse]:
        """Accept an ordered list of image IDs and persist their positions."""
        for position, image_id in enumerate(ordered_ids):
            await VenueImage.filter(id=image_id, venue_id=venue_id).update(
                order=position
            )
        return await self.list_for_venue(venue_id)


class VenueUnavailabilityCRUD(CRUD[VenueUnavailability, VenueUnavailabilityResponse]):  # type: ignore
    async def create_for_venue(
        self, venue_id: UUID, payload: VenueUnavailabilityCreate
    ) -> VenueUnavailabilityResponse:
        inst = await VenueUnavailability.create(
            venue_id=venue_id,
            **payload.model_dump(),
        )
        return VenueUnavailabilityResponse.model_validate(inst, from_attributes=True)

    async def update(
        self,
        unavailability_id: UUID,
        venue_id: UUID,
        payload: VenueUnavailabilityUpdate,
    ) -> VenueUnavailabilityResponse | None:
        inst = await VenueUnavailability.get_or_none(
            id=unavailability_id, venue_id=venue_id
        )
        if not inst:
            return None

        await inst.update_from_dict(payload.model_dump(exclude_none=True)).save()
        return VenueUnavailabilityResponse.model_validate(inst, from_attributes=True)

    async def delete(self, unavailability_id: UUID, venue_id: UUID) -> bool:
        return await self.delete_by(id=unavailability_id, venue_id=venue_id)

    async def list_for_venue(self, venue_id: UUID) -> list[VenueUnavailabilityResponse]:
        items = await VenueUnavailability.filter(venue_id=venue_id).order_by(
            "start_datetime"
        )
        return [
            VenueUnavailabilityResponse.model_validate(item, from_attributes=True)
            for item in items
        ]


class VenueCRUD(CRUD[Venue, VenueResponse]):  # type: ignore
    async def create_venue(self, payload: VenueCreate, owner_id: UUID) -> VenueResponse:
        inst = await Venue.create(
            owner_id=owner_id,
            **payload.model_dump(),
        )
        await inst.fetch_related("images", "unavailabilities")
        return VenueResponse.model_validate(inst, from_attributes=True)

    async def update_venue(
        self, venue_id: UUID, payload: VenueUpdate, owner_id: UUID
    ) -> VenueResponse | None:
        inst = await Venue.get_or_none(id=venue_id, owner_id=owner_id)
        if not inst:
            return None

        await inst.update_from_dict(payload.model_dump(exclude_none=True)).save()
        await inst.fetch_related("images", "unavailabilities")
        return VenueResponse.model_validate(inst, from_attributes=True)

    async def update_status(
        self, venue_id: UUID, payload: VenueStatusUpdate
    ) -> VenueResponse | None:
        """Admin-only — no ownership check."""
        inst = await Venue.get_or_none(id=venue_id)
        if not inst:
            return None

        inst.status = payload.status  # type: ignore
        await inst.save(update_fields=["status"])
        await inst.fetch_related("images", "unavailabilities")
        return VenueResponse.model_validate(inst, from_attributes=True)

    async def delete_venue(self, venue_id: UUID, owner_id: UUID) -> bool:
        """Owners can only delete their own venues."""
        return await self.delete_by(id=venue_id, owner_id=owner_id)

    async def admin_delete_venue(self, venue_id: UUID) -> bool:
        return await self.delete_by(id=venue_id)

    async def get_venue(self, venue_id: UUID) -> VenueResponse | None:
        inst = await Venue.get_or_none(id=venue_id).prefetch_related(
            "images", "unavailabilities"
        )

        if not inst:
            return None

        return VenueResponse.model_validate(inst, from_attributes=True)

    async def get_venue_for_owner(
        self, venue_id: UUID, owner_id: UUID
    ) -> VenueResponse | None:
        try:
            inst = await Venue.get(id=venue_id, owner_id=owner_id).prefetch_related(
                "images", "unavailabilities"
            )
        except DoesNotExist:
            return None
        return VenueResponse.model_validate(inst, from_attributes=True)

    async def list_venues(self, filters: VenueFilters) -> list[VenueListItem]:
        qs = Venue.all()

        if filters.status is not None:
            qs = qs.filter(status=filters.status)
        if filters.city is not None:
            qs = qs.filter(city__icontains=filters.city)
        if filters.sport_type is not None:
            # for SQLite use a raw .filter() override
            qs = qs.filter(sport_types__contains=filters.sport_type.value)
        if filters.is_indoor is not None:
            qs = qs.filter(is_indoor=filters.is_indoor)
        if filters.has_parking is not None:
            qs = qs.filter(has_parking=filters.has_parking)
        if filters.min_price is not None:
            qs = qs.filter(price_per_hour__gte=filters.min_price)
        if filters.max_price is not None:
            qs = qs.filter(price_per_hour__lte=filters.max_price)
        if filters.min_capacity is not None:
            qs = qs.filter(capacity__gte=filters.min_capacity)

        offset = (filters.page - 1) * filters.page_size
        qs = qs.offset(offset).limit(filters.page_size)

        venues = await qs.prefetch_related("images")

        results: list[VenueListItem] = []
        for v in venues:
            thumbnail = next(
                (img.url for img in v.images if img.is_thumbnail),  # type: ignore[union-attr]
                None,
            )
            results.append(
                VenueListItem(
                    id=v.id,
                    name=v.name,
                    city=v.city,
                    sport_types=v.sport_types,
                    status=VenueStatus(v.status),
                    price_per_hour=v.price_per_hour,
                    currency=v.currency,
                    capacity=v.capacity,
                    is_indoor=v.is_indoor,
                    rating=v.rating,
                    total_reviews=v.total_reviews,
                    thumbnail=thumbnail,
                )
            )
        return results


venue_crud = VenueCRUD(Venue, VenueResponse)
venue_image_crud = VenueImageCRUD(VenueImage, VenueImageResponse)
venue_unavailability_crud = VenueUnavailabilityCRUD(
    VenueUnavailability, VenueUnavailabilityResponse
)


async def assert_owns_venue(venue_id: UUID, current_user: CurrentUser) -> None:
    """Admins bypass ownership; regular users must own the venue."""
    if VenueScope.ADMIN_WRITE in current_user.scopes:
        return
    venue = await venue_crud.get_venue(venue_id)
    if not venue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found"
        )
    if venue.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to modify this venue",
        )
