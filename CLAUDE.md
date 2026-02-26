# CLAUDE.md — ploshtadka-venues-ms

FastAPI microservice for managing sports venues (part of the PloshtadkaBG platform).

## Package management

Always use `uv`. Never use `pip` directly.

```bash
uv add <package>       # add dependency
uv sync                # install from lockfile
uv run <command>       # run in the venv
```

## Running

```bash
uv run pytest                                                     # run tests
uv run uvicorn main:application --host 0.0.0.0 --port 8001       # dev server
```

## Architecture

### Technology Stack

- **API Framework**: FastAPI with Gunicorn/Uvicorn
- **Database**: PostgreSQL with Tortoise ORM and Aerich migrations
- **Testing**: pytest with custom markers and fixtures

## Auth architecture — critical

Auth is delegated entirely to Traefik via `forwardAuth`. The JWT is validated at the gateway; this service only reads the headers Traefik injects after a successful check:

| Header          | Type   | Description                        |
|-----------------|--------|------------------------------------|
| `X-User-ID`     | UUID   | Authenticated user's ID            |
| `X-Username`    | string | Authenticated user's username      |
| `X-User-Scopes` | string | Space-separated list of scopes     |

`get_current_user()` in `app/deps.py` reads these headers — it does not validate any token itself. **Do not add JWT validation middleware inside this service.**

The service is designed to run behind Traefik. Direct calls without those headers will receive 422.

## Project structure

```
app/
  settings.py          # DB_URL, USERS_MS_URL (env vars with defaults)
  models.py            # Tortoise ORM models (Venue, VenueImage, VenueUnavailability)
  schemas.py           # Pydantic schemas — enums mirrored from models.py
  crud.py              # Data access layer, extends ms_core.CRUD
  deps.py              # Auth dependencies and pre-built scope checkers
  scopes.py            # VenueScope StrEnum + VENUE_SCOPE_DESCRIPTIONS
  routers/
    venue.py           # /venues CRUD
    images.py          # /venues/{id}/images
    unavail.py         # /venues/{id}/unavailabilities
tests/
  conftest.py          # Fixtures: owner_client, admin_client, anon_app, client_factory
  factories.py         # make_user(), make_admin(), venue_create_payload(), etc.
  test_*.py            # One file per router + edge cases + schemas + scopes
```

## ms-core

`ms-core` is an internal library sourced from GitHub (`HexChap/MSCore`). It provides:

- `ms_core.CRUD[Model, ResponseSchema]` — base class for all CRUD operations
- `ms_core.setup_app(app, db_url, routers_path, models)` — wires Tortoise ORM and auto-discovers all router files under `routers_path`

New router files placed in `app/routers/` are picked up automatically by `setup_app` — no manual registration needed.

## Key formats

**VenueStatus** enum: `pending` | `active` | `rejected` | `suspended`

**`working_hours`** JSON (stored on Venue): weekday keys `"0"`–`"6"` (0=Monday), value `{open: "HH:MM", close: "HH:MM"}` or `null` for closed days.

**`sport_types`**: JSON list of strings (e.g. `["football", "tennis"]`).

## Cache headers

`GET /venues/` — `Cache-Control: public, max-age=30`
`GET /venues/{id}` — `Cache-Control: public, max-age=60`

Set in the router. Downstream caches (Traefik/browser) serve stale data within the TTL — keep this in mind when testing updates.

## Adding a new resource

1. Add Tortoise model to `app/models.py`
2. Add Pydantic schemas to `app/schemas.py` (mirror any new enums from models)
3. Create a CRUD class in `app/crud.py` extending `ms_core.CRUD`
4. Create `app/routers/<resource>.py` — auto-discovered, no extra wiring
5. Add relevant scopes to `app/scopes.py` following the `resource:action` / `admin:resource:action` pattern
6. Wire scope deps in `app/deps.py`

## Authorization patterns

Use the pre-built dependencies from `app/deps.py`:

```python
# Owner only
Depends(can_write_venue)

# Owner or admin (preferred for mutating operations)
Depends(can_write_or_admin)

# Admin only
Depends(can_admin_write)

# Custom scopes
Depends(require_scopes(VenueScope.READ, VenueScope.ME))
```

`_owner_or_admin()` passes if the user has the owner-level scope OR the admin-level scope OR the top-level `admin:venues` scope.

`is_admin` on `CurrentUser` checks for `admin:scopes` (the global admin scope, not venue-specific).

## Testing conventions

- **Mock the CRUD layer**, not the database. Use `unittest.mock.AsyncMock`.
- Use `owner_client` / `admin_client` fixtures for most tests.
- Use `anon_app` when you need the real auth/scope deps to run (401/403 assertions).
- Use `client_factory(make_user(scopes=[...]))` for custom scope combinations.
- Build test data with factories from `tests/factories.py`, not inline dicts.

```python
from unittest.mock import AsyncMock, patch

def test_create_venue(owner_client):
    payload = venue_create_payload()
    with patch("app.routers.venue.crud.create_venue", new_callable=AsyncMock) as mock:
        mock.return_value = venue_response()
        resp = owner_client.post("/venues", json=payload)
    assert resp.status_code == 201
```

## Database

- Development/tests: SQLite in-memory (`sqlite://:memory:`, default)
- Production: PostgreSQL (`DB_URL` env var)
- Migrations: Aerich — config in `pyproject.toml`, stored in `./migrations/`

```bash
uv run aerich migrate --name <description>   # generate migration
uv run aerich upgrade                        # apply migrations
```

## Environment variables

| Variable       | Default                  | Description                        |
|----------------|--------------------------|------------------------------------|
| `DB_URL`       | `sqlite://:memory:`      | Database connection string         |
| `USERS_MS_URL` | `http://localhost:8000`  | Users microservice base URL        |
