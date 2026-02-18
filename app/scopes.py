from enum import StrEnum

from fastapi import Depends

from app.deps import CurrentUser, get_active_user, require_scopes


class VenueScope(StrEnum):
    READ = "venues:read"
    ME = "venues:me"
    WRITE = "venues:write"
    DELETE = "venues:delete"
    IMAGES = "venues:images"
    SCHEDULE = "venues:schedule"

    ADMIN = "admin:scopes"
    ADMIN_READ = "admin:venues:read"
    ADMIN_WRITE = "admin:venues:write"
    ADMIN_DELETE = "admin:venues:delete"


VENUE_SCOPE_DESCRIPTIONS: dict[str, str] = {
    VenueScope.READ: "Browse and search public venue listings.",
    VenueScope.ME: "Read your own venues and their details.",
    VenueScope.WRITE: "Create and update your own venues.",
    VenueScope.DELETE: "Delete your own venues.",
    VenueScope.IMAGES: "Upload and manage images for your own venues.",
    VenueScope.SCHEDULE: "Manage unavailability windows for your own venues.",
    VenueScope.ADMIN_READ: "Read any venue regardless of status (admin).",
    VenueScope.ADMIN_WRITE: "Edit any venue and change its status (admin).",
    VenueScope.ADMIN_DELETE: "Hard-delete any venue (admin).",
}

can_read_venues = require_scopes(VenueScope.READ)
can_read_own_venues = require_scopes(VenueScope.ME)
can_write_venue = require_scopes(VenueScope.WRITE)
can_delete_venue = require_scopes(VenueScope.DELETE)
can_manage_images = require_scopes(VenueScope.IMAGES)
can_manage_schedule = require_scopes(VenueScope.SCHEDULE)
can_admin_read = require_scopes(VenueScope.ADMIN_READ)
can_admin_write = require_scopes(VenueScope.ADMIN_READ, VenueScope.ADMIN_WRITE)
can_admin_delete = require_scopes(
    VenueScope.ADMIN_READ,
    VenueScope.ADMIN_WRITE,
    VenueScope.ADMIN_DELETE,
)


def _owner_or_admin(owner_scope: VenueScope, admin_scope: VenueScope):
    """
    Returns a dependency that passes if the user has EITHER:
      - the owner-level scope, OR
      - the admin-level scope
    Raises 403 otherwise.
    """

    async def _dep(
        current_user: CurrentUser = Depends(get_active_user),
    ) -> CurrentUser:
        has_owner = owner_scope in current_user.scopes
        has_admin = admin_scope in current_user.scopes

        if not (has_owner or has_admin):
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Requires '{owner_scope}' (for your own venues) "
                    f"or '{admin_scope}' (admin)."
                ),
            )
        return current_user

    return _dep


can_write_or_admin = _owner_or_admin(VenueScope.WRITE, VenueScope.ADMIN_WRITE)
can_delete_or_admin = _owner_or_admin(VenueScope.DELETE, VenueScope.ADMIN_DELETE)
can_images_or_admin = _owner_or_admin(VenueScope.IMAGES, VenueScope.ADMIN_WRITE)
can_schedule_or_admin = _owner_or_admin(VenueScope.SCHEDULE, VenueScope.ADMIN_WRITE)
