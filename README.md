# ploshtadka-venues-ms

Manages sports venues, images, and unavailability periods.

**Port:** `8001` | **Prefix:** `/venues`

## Endpoints

| Method | Path | Auth |
|---|---|---|
| `GET` | `/venues` | Public |
| `GET` | `/venues/{id}` | Public |
| `POST` | `/venues` | Owner scope |
| `PATCH` | `/venues/{id}` | Owner / Admin |
| `DELETE` | `/venues/{id}` | Owner / Admin |
| `*` | `/venues/{id}/images` | Owner / Admin |
| `*` | `/venues/{id}/unavailabilities` | Owner / Admin |

## Running

```bash
uv run uvicorn main:application --host 0.0.0.0 --port 8001
uv run pytest
```

## Key env vars

| Variable | Default |
|---|---|
| `DB_URL` | `sqlite://:memory:` |
| `USERS_MS_URL` | `http://localhost:8000` |

## Notes

- Auth is delegated to Traefik — reads `X-User-Id`, `X-Username`, `X-User-Scopes` headers.
- `GET /venues` and `GET /venues/{id}` carry `Cache-Control: public` headers (max-age 30s / 60s).
- Tests mock the CRUD layer with `AsyncMock`; use `owner_client`/`admin_client`/`anon_app` fixtures.
