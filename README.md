# Water Asset System

A small FastAPI + SQLAlchemy service for tracking water-utility assets
(pumps, pipes, valves) and their inspections. Built as a Python refresher
that exercises eight core topics in one realistic project.

## Quick start (Windows)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"        # installs app + test deps from pyproject.toml

uvicorn app.main:app --reload  # http://127.0.0.1:8000/docs  (Swagger UI)
pytest                         # run the test suite
```

On macOS/Linux the only difference is `source .venv/bin/activate`.

## Where each topic lives

| # | Topic | Where to look |
|---|-------|---------------|
| 1 | Virtual environments | the `.venv` you create above; `requirements.txt` |
| 2 | Packaging | `pyproject.toml` (`pip install -e .` makes `app` importable) |
| 3 | Type hints | everywhere — `Mapped[int]`, `-> User \| None`, schema fields |
| 4 | Classes & inheritance | `app/models.py`: `Asset` → `Pump`/`Pipe`/`Valve`, with `risk_score()` overridden per subtype |
| 5 | Async/await | `app/crud.py`, routers, and `tests/` all use `async`/`await` |
| 6 | pytest | `tests/` — fixtures in `conftest.py`, `parametrize`, plain asserts |
| 7 | FastAPI | `app/main.py`, `app/routers/` — DI via `Depends`, Pydantic DTOs |
| 8 | SQLAlchemy | `app/models.py` (ORM + relationship), `app/crud.py` (async queries) |

## API surface

```
GET    /health
POST   /assets/pumps          POST /assets/pipes    POST /assets/valves
GET    /assets                (filters: ?status= &asset_type=)
GET    /assets/{id}
GET    /assets/{id}/health    -> latest condition + polymorphic risk score
POST   /assets/{id}/inspections
GET    /assets/{id}/inspections
```

## Notes for a C# developer

- `pyproject.toml` ≈ your `.csproj`; the venv replaces per-project NuGet isolation.
- `Asset`/`Pump`/`Pipe`/`Valve` use **single-table inheritance** — SQLAlchemy's
  version of EF Core's Table-Per-Hierarchy (one table, an `asset_type` discriminator).
- `with_polymorphic="*"` on the base mapper forces subclass columns to load
  eagerly; without it, async code hits a lazy-load error.
- `Depends(get_db)` is the DI container handing each request a scoped session,
  just like an injected `DbContext`.
- For your real MySQL database, change `DATABASE_URL` in `app/database.py` to
  a `mysql+asyncmy://...` URL and add Alembic for migrations (the EF Migrations
  analog) instead of `create_all`.

## Suggested extensions (to keep learning)

1. Add `PATCH /assets/{id}/status` to move an asset to `maintenance`.
2. Add a `MaintenanceJob` model (one-to-many off `Asset`) and a router for it.
3. Add Alembic and generate your first migration.
4. Add a `GET /assets/at-risk` endpoint that returns assets sorted by `risk_score()`.
5. Swap SQLite for your MySQL Workbench schema and re-run the tests.
