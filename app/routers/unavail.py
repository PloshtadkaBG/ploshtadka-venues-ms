from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.crud import assert_owns_venue, venue_unavailability_crud
from app.deps import (
    CurrentUser,
    can_read_venues,
    can_schedule_or_admin,
)
from app.schemas import (
    VenueUnavailabilityCreate,
    VenueUnavailabilityResponse,
    VenueUnavailabilityUpdate,
)

router = APIRouter(
    prefix="/venues/{venue_id}/unavailabilities", tags=["Venue Unavailabilities"]
)


@router.get(
    "",
    response_model=list[VenueUnavailabilityResponse],
    dependencies=[Depends(can_read_venues)],
)
async def list_unavailabilities(venue_id: UUID):
    return await venue_unavailability_crud.list_for_venue(venue_id)


@router.post(
    "",
    response_model=VenueUnavailabilityResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_unavailability(
    venue_id: UUID,
    payload: VenueUnavailabilityCreate,
    current_user: CurrentUser = Depends(can_schedule_or_admin),
):
    await assert_owns_venue(venue_id, current_user)
    return await venue_unavailability_crud.create_for_venue(venue_id, payload)


@router.patch("/{unavailability_id}", response_model=VenueUnavailabilityResponse)
async def update_unavailability(
    venue_id: UUID,
    unavailability_id: UUID,
    payload: VenueUnavailabilityUpdate,
    current_user: CurrentUser = Depends(can_schedule_or_admin),
):
    await assert_owns_venue(venue_id, current_user)
    item = await venue_unavailability_crud.update(unavailability_id, venue_id, payload)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unavailability not found"
        )
    return item


@router.delete("/{unavailability_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unavailability(
    venue_id: UUID,
    unavailability_id: UUID,
    current_user: CurrentUser = Depends(can_schedule_or_admin),
):
    await assert_owns_venue(venue_id, current_user)
    deleted = await venue_unavailability_crud.delete(unavailability_id, venue_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unavailability not found"
        )
