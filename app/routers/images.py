from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.crud import assert_owns_venue, venue_image_crud
from app.deps import (
    CurrentUser,
    can_images_or_admin,
)
from app.schemas import (
    VenueImageCreate,
    VenueImageResponse,
    VenueImageUpdate,
)

router = APIRouter(prefix="/venues/{venue_id}/images", tags=["Venue Images"])


@router.get("", response_model=list[VenueImageResponse])
async def list_images(venue_id: UUID):
    return await venue_image_crud.list_for_venue(venue_id)


@router.post(
    "",
    response_model=VenueImageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_image(
    venue_id: UUID,
    payload: VenueImageCreate,
    current_user: CurrentUser = Depends(can_images_or_admin),
):
    await assert_owns_venue(venue_id, current_user)
    return await venue_image_crud.create_for_venue(venue_id, payload)


@router.patch("/{image_id}", response_model=VenueImageResponse)
async def update_image(
    venue_id: UUID,
    image_id: UUID,
    payload: VenueImageUpdate,
    current_user: CurrentUser = Depends(can_images_or_admin),
):
    await assert_owns_venue(venue_id, current_user)
    img = await venue_image_crud.update(image_id, venue_id, payload)
    if not img:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )
    return img


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    venue_id: UUID,
    image_id: UUID,
    current_user: CurrentUser = Depends(can_images_or_admin),
):
    await assert_owns_venue(venue_id, current_user)
    deleted = await venue_image_crud.delete(image_id, venue_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )


@router.put("/reorder", response_model=list[VenueImageResponse])
async def reorder_images(
    venue_id: UUID,
    ordered_ids: list[UUID],
    current_user: CurrentUser = Depends(can_images_or_admin),
):
    await assert_owns_venue(venue_id, current_user)
    return await venue_image_crud.reorder(venue_id, ordered_ids)
