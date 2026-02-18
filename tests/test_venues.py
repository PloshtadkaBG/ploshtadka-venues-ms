from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.schemas import VenueResponse
from app.scopes import VenueScope

from .factories import (
    OWNER_ID,
    VENUE_ID,
    make_admin,
    make_user,
    venue_list_item,
    venue_response,
)


class TestListVenues:
    def test_returns_200(self, client_factory):
        with patch("app.routers.venue.venue_crud") as mock_crud:
            mock_crud.list_venues = AsyncMock(return_value=[venue_list_item()])
            resp = client_factory(make_user()).get("/venues")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_empty_list(self, client_factory):
        with patch("app.routers.venue.venue_crud") as mock_crud:
            mock_crud.list_venues = AsyncMock(return_value=[])
            resp = client_factory(make_user()).get("/venues")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_filters_forwarded(self, client_factory):
        with patch("app.routers.venue.venue_crud") as mock_crud:
            mock_crud.list_venues = AsyncMock(return_value=[])
            resp = client_factory(make_user()).get(
                "/venues", params={"city": "Sofia", "is_indoor": True, "page": 2}
            )
        assert resp.status_code == 200
        call_filters = mock_crud.list_venues.call_args[0][0]
        assert call_filters.city == "Sofia"
        assert call_filters.is_indoor is True
        assert call_filters.page == 2


class TestGetVenue:
    def test_existing_venue_returns_200(self, client_factory):
        with patch("app.routers.venue.venue_crud") as mock_crud:
            mock_crud.get_venue = AsyncMock(return_value=venue_response())
            resp = client_factory(make_user()).get(f"/venues/{VENUE_ID}")
        assert resp.status_code == 200
        assert resp.json()["id"] == str(VENUE_ID)

    def test_missing_venue_returns_404(self, client_factory):
        with patch("app.routers.venue.venue_crud") as mock_crud:
            mock_crud.get_venue = AsyncMock(return_value=None)
            resp = client_factory(make_user()).get(f"/venues/{VENUE_ID}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Venue not found"


class TestCreateVenue:
    PAYLOAD = {
        "name": "Tennis Club Sofia",
        "description": "A great place for tennis lovers.",
        "address": "1 Sports Ave",
        "city": "Sofia",
        "price_per_hour": "25.00",
        "sport_types": ["tennis"],
    }

    def test_owner_can_create(self, client_factory):
        with patch("app.routers.venue.venue_crud") as mock_crud:
            mock_crud.create_venue = AsyncMock(return_value=venue_response())
            resp = client_factory(make_user()).post("/venues", json=self.PAYLOAD)
        assert resp.status_code == 201
        mock_crud.create_venue.assert_awaited_once()

    def test_owner_id_injected_from_auth(self, client_factory):
        """owner_id must come from the token, not the request body."""
        with patch("app.routers.venue.venue_crud") as mock_crud:
            mock_crud.create_venue = AsyncMock(return_value=venue_response())
            client_factory(make_user(user_id=OWNER_ID)).post(
                "/venues", json=self.PAYLOAD
            )
        _, kwargs = mock_crud.create_venue.call_args
        assert kwargs["owner_id"] == OWNER_ID

    def test_invalid_payload_returns_422(self, client_factory):
        resp = client_factory(make_user()).post("/venues", json={"name": "X"})
        assert resp.status_code == 422

    def test_user_without_write_scope_gets_403(self, anon_app):
        from app.deps import get_current_user

        async def _non_admin_user():
            return make_user(scopes=[VenueScope.READ])

        anon_app.dependency_overrides[get_current_user] = _non_admin_user
        with TestClient(anon_app) as c:
            resp = c.post("/venues", json=self.PAYLOAD)

        assert resp.status_code == 403


class TestUpdateVenue:
    PATCH = {"name": "Renamed Court"}

    def test_owner_can_update_own_venue(self, client_factory):
        with patch("app.routers.venue.venue_crud") as mock_crud:
            mock_crud.update_venue = AsyncMock(
                return_value=venue_response(name="Renamed Court")
            )
            resp = client_factory(make_user()).patch(
                f"/venues/{VENUE_ID}", json=self.PATCH
            )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed Court"

    def test_returns_404_when_not_owner(self, client_factory):
        with patch("app.routers.venue.venue_crud") as mock_crud:
            mock_crud.update_venue = AsyncMock(return_value=None)
            resp = client_factory(make_user()).patch(
                f"/venues/{VENUE_ID}", json=self.PATCH
            )
        assert resp.status_code == 404

    def test_admin_bypasses_ownership(self, client_factory):
        with patch("app.routers.venue.venue_crud") as mock_crud:
            existing = VenueResponse(**venue_response())
            mock_crud.get_venue = AsyncMock(return_value=existing)
            mock_crud.update_venue = AsyncMock(
                return_value=venue_response(name="Admin Edit")
            )
            resp = client_factory(make_admin()).patch(
                f"/venues/{VENUE_ID}", json=self.PATCH
            )
        assert resp.status_code == 200
        # Admin path calls get_venue first to resolve owner_id
        mock_crud.get_venue.assert_awaited_once_with(VENUE_ID)

    def test_admin_404_when_venue_missing(self, client_factory):
        with patch("app.routers.venue.venue_crud") as mock_crud:
            mock_crud.get_venue = AsyncMock(return_value=None)
            resp = client_factory(make_admin()).patch(
                f"/venues/{VENUE_ID}", json=self.PATCH
            )
        assert resp.status_code == 404


class TestUpdateVenueStatus:
    def test_admin_can_change_status(self, client_factory):
        with patch("app.routers.venue.venue_crud") as mock_crud:
            mock_crud.update_status = AsyncMock(
                return_value=venue_response(status="inactive")
            )
            resp = client_factory(make_admin()).patch(
                f"/venues/{VENUE_ID}/status", json={"status": "inactive"}
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "inactive"

    def test_invalid_status_returns_422(self, client_factory):
        resp = client_factory(make_admin()).patch(
            f"/venues/{VENUE_ID}/status", json={"status": "flying"}
        )
        assert resp.status_code == 422

    def test_non_admin_gets_403(self, anon_app):
        """Non-admin users should be rejected before the route handler runs."""
        from app.deps import get_current_user

        async def _non_admin_user():
            return make_user(scopes=[VenueScope.READ])

        anon_app.dependency_overrides[get_current_user] = _non_admin_user

        with TestClient(anon_app) as client:
            resp = client.patch(
                f"/venues/{VENUE_ID}/status", json={"status": "inactive"}
            )

        assert resp.status_code == 403


class TestDeleteVenue:
    def test_owner_deletes_own_venue(self, client_factory):
        with patch("app.routers.venue.venue_crud") as mock_crud:
            mock_crud.delete_venue = AsyncMock(return_value=True)
            resp = client_factory(make_user()).delete(f"/venues/{VENUE_ID}")
        assert resp.status_code == 204

    def test_owner_404_when_not_found(self, client_factory):
        with patch("app.routers.venue.venue_crud") as mock_crud:
            mock_crud.delete_venue = AsyncMock(return_value=False)
            resp = client_factory(make_user()).delete(f"/venues/{VENUE_ID}")
        assert resp.status_code == 404

    def test_admin_uses_admin_delete(self, client_factory):
        with patch("app.routers.venue.venue_crud") as mock_crud:
            mock_crud.admin_delete_venue = AsyncMock(return_value=True)
            resp = client_factory(make_admin()).delete(f"/venues/{VENUE_ID}")
        assert resp.status_code == 204
        mock_crud.admin_delete_venue.assert_awaited_once_with(VENUE_ID)
        mock_crud.delete_venue.assert_not_called()

    def test_admin_404_when_not_found(self, client_factory):
        with patch("app.routers.venue.venue_crud") as mock_crud:
            mock_crud.admin_delete_venue = AsyncMock(return_value=False)
            resp = client_factory(make_admin()).delete(f"/venues/{VENUE_ID}")
        assert resp.status_code == 404
