from enum import StrEnum


class VenueScope(StrEnum):
    READ = "venues:read"
    ME = "venues:me"
    WRITE = "venues:write"
    DELETE = "venues:delete"
    IMAGES = "venues:images"
    SCHEDULE = "venues:schedule"

    ADMIN = "admin:venues"
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
