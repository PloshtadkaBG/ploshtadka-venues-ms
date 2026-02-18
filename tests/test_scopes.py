from app.scopes import VenueScope

from .factories import make_admin, make_user


class TestCurrentUserScopes:
    def test_admin_detected_by_scope(self):
        admin = make_admin()
        assert admin.is_admin is True

    def test_regular_user_not_admin(self):
        user = make_user()
        assert user.is_admin is False

    def test_scoped_user_missing_admin_scope(self):
        user = make_user(scopes=[VenueScope.READ, VenueScope.WRITE])
        assert VenueScope.ADMIN_WRITE not in user.scopes
