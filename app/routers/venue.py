from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.crud import venue_crud
from app.deps import CurrentUser
from app.schemas import (
    VenueCreate,
    VenueFilters,
    VenueListItem,
    VenueResponse,
    VenueStatusUpdate,
    VenueUpdate,
)
from app.scopes import (
    VenueScope,
    can_admin_write,
    can_delete_or_admin,
    can_read_venues,
    can_write_or_admin,
)

router = APIRouter(prefix="/venues", tags=["venues"])


@router.get(
    "/",
    dependencies=[Depends(can_read_venues)],
)
async def list_venues(filters: VenueFilters = Depends()) -> list[VenueListItem]:
    return await venue_crud.list_venues(filters)


@router.post("/", response_model=VenueResponse, status_code=status.HTTP_201_CREATED)
async def create_venue(
    payload: VenueCreate,
    current_user: CurrentUser = Depends(can_write_or_admin),
):
    return await venue_crud.create_venue(payload, owner_id=current_user.id)


@router.get(
    "/{venue_id}",
    response_model=VenueResponse,
    dependencies=[Depends(can_read_venues)],
)
async def get_venue(venue_id: UUID):
    venue = await venue_crud.get_venue(venue_id)
    if not venue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found"
        )
    return venue


@router.patch("/{venue_id}", response_model=VenueResponse)
async def update_venue(
    venue_id: UUID,
    payload: VenueUpdate,
    current_user: CurrentUser = Depends(can_write_or_admin),
):
    # Admins can edit any venue; owners only their own.
    if VenueScope.ADMIN_WRITE in current_user.scopes:
        venue = await venue_crud.get_venue(venue_id)
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found"
            )
        venue = await venue_crud.update_venue(
            venue_id, payload, owner_id=venue.owner_id
        )
    else:
        venue = await venue_crud.update_venue(
            venue_id, payload, owner_id=current_user.id
        )

    if not venue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found or you don't own it",
        )
    return venue


@router.patch(
    "/{venue_id}/status",
    response_model=VenueResponse,
    dependencies=[Depends(can_admin_write)],
)
async def update_venue_status(venue_id: UUID, payload: VenueStatusUpdate):
    venue = await venue_crud.update_status(venue_id, payload)
    if not venue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found"
        )
    return venue


@router.delete("/{venue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_venue(
    venue_id: UUID,
    current_user: CurrentUser = Depends(can_delete_or_admin),
):
    if VenueScope.ADMIN_DELETE in current_user.scopes:
        deleted = await venue_crud.admin_delete_venue(venue_id)
    else:
        deleted = await venue_crud.delete_venue(venue_id, owner_id=current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found or you don't own it",
        )
