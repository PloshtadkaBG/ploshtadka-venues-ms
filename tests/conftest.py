"""
Shared pytest fixtures available to every test file automatically.
No imports needed in test files — pytest discovers this by convention.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deps import get_active_user, get_current_user
from app.routers.venue import router
from app.scopes import (
    can_admin_write,
    can_delete_or_admin,
    can_images_or_admin,
    can_read_own_venues,
    can_read_venues,
    can_schedule_or_admin,
    can_write_or_admin,
)

from .factories import make_admin, make_user

# ---------------------------------------------------------------------------
# App builder — used by all client fixtures
# ---------------------------------------------------------------------------


def build_app(current_user) -> FastAPI:
    """
    Fresh FastAPI app with every auth/scope dependency overridden to return
    `current_user` unconditionally. Tests that need the *real* dep to run
    (e.g. scope-rejection tests) should build their own app manually.
    """
    app = FastAPI()
    app.include_router(router)

    async def _user():
        return current_user

    for dep in (
        can_read_venues,
        can_read_own_venues,
        can_write_or_admin,
        can_delete_or_admin,
        can_images_or_admin,
        can_schedule_or_admin,
        can_admin_write,
        get_active_user,
        get_current_user,
    ):
        app.dependency_overrides[dep] = _user

    return app


# ---------------------------------------------------------------------------
# Reusable client fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def owner_client():
    """TestClient authenticated as a regular venue owner."""
    return TestClient(build_app(make_user()), raise_server_exceptions=True)


@pytest.fixture()
def admin_client():
    """TestClient authenticated as an admin."""
    return TestClient(build_app(make_admin()), raise_server_exceptions=True)


@pytest.fixture()
def anon_app():
    """
    Bare app with NO dependency overrides.
    Use this when you want real scope/auth deps to run so you can assert 401/403.
    """
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture()
def client_factory():
    """
    Callable fixture: call it with any CurrentUser to get a scoped TestClient.

    Usage in a test:
        def test_something(client_factory):
            client = client_factory(make_user(scopes=[VenueScope.READ]))
            resp = client.get("/venues")
    """

    def _make(current_user) -> TestClient:
        return TestClient(build_app(current_user), raise_server_exceptions=True)

    return _make
