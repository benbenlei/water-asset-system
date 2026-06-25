# Water Asset System

A small FastAPI + SQLAlchemy service for tracking water-utility assets
(pumps, pipes, valves), their inspections, and maintenance jobs. Built as a
Python refresher that exercises eight core topics in one realistic project.

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
GET    /assets/at-risk        -> all assets sorted by risk_score() desc
GET    /assets/{id}
PATCH  /assets/{id}/status    -> move to active | inactive | maintenance
GET    /assets/{id}/health    -> latest condition + polymorphic risk score

POST   /assets/{id}/inspections
GET    /assets/{id}/inspections

POST   /assets/{id}/maintenance-jobs
GET    /assets/{id}/maintenance-jobs
GET    /maintenance-jobs/{id}
PATCH  /maintenance-jobs/{id}/status   -> lifecycle transitions (see below)
```

### MaintenanceJob lifecycle

Jobs move through `scheduled → in_progress → completed | cancelled`.
`completed` and `cancelled` are terminal — no further transitions.

| Field | Notes |
|---|---|
| `assigned_to` | Free-text name of the responsible technician |
| `scheduled_date` | Date the work is planned |
| `outcome` | Required on completion: `resolved`, `partially_resolved`, or `deferred` |
| `post_job_condition` | Optional 1–5 score recorded by the technician on completion |
| `completed_at` | Set automatically when the job transitions to `completed` |

When `post_job_condition` is set on a completed job, it overrides the
inspection-based condition in `risk_score()` — but only until a newer
inspection is recorded. After that the inspection takes precedence again.

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

1. Add Alembic and generate your first migration.
2. Swap SQLite for your MySQL Workbench schema and re-run the tests.
3. Add pagination (`limit`/`offset`) to `GET /assets/{id}/maintenance-jobs`.
4. Add a `Technician` model and replace the free-text `assigned_to` field.
