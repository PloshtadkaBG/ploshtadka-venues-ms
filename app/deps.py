from dataclasses import dataclass, field
from functools import lru_cache
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app import settings

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.users_ms_url}/auth/token",
    scopes={
        "users:read": "Read users data.",
        "users:me": "Read current user profile.",
        "admin:scopes": "Manage user scopes.",
    },
)


@dataclass
class CurrentUser:
    id: UUID
    username: str
    full_name: str | None
    email: str | None
    is_active: bool
    scopes: list[str] = field(default_factory=list)

    @property
    def is_admin(self) -> bool:
        return "admin:scopes" in self.scopes


@lru_cache(maxsize=1)
def _get_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.users_ms_url,
        timeout=httpx.Timeout(5.0),
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> CurrentUser:
    """
    Calls GET /users/@me/get on the users-ms with the bearer token.
    Returns a CurrentUser or raises 401.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    client = _get_http_client()
    try:
        resp = await client.get(
            "/users/@me/get",
            headers={"Authorization": f"Bearer {token}"},
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Users service unreachable: {exc}",
        )

    if resp.status_code == status.HTTP_401_UNAUTHORIZED:
        raise credentials_exc

    if resp.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Users service returned unexpected status {resp.status_code}",
        )

    data = resp.json()
    return CurrentUser(
        id=data["id"],
        username=data["username"],
        full_name=data.get("full_name"),
        email=data.get("email"),
        is_active=data.get("is_active", True),
        scopes=data.get("scopes") or [],
    )


async def get_active_user(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Rejects soft-deactivated accounts."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated",
        )
    return current_user


def require_scopes(*required: str):
    """
    Factory that returns a dependency enforcing one or more scopes.

    Usage:
        @router.get("/admin-only")
        async def admin_route(user = Depends(require_scopes("admin:scopes"))):
            ...
    """

    async def _dep(
        current_user: CurrentUser = Depends(get_active_user),
    ) -> CurrentUser:
        missing = [s for s in required if s not in current_user.scopes]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scopes: {', '.join(missing)}",
            )
        return current_user

    return _dep


async def require_admin(
    current_user: CurrentUser = Depends(require_scopes("admin:scopes")),
) -> CurrentUser:
    """Shorthand for admin-only endpoints."""
    return current_user
