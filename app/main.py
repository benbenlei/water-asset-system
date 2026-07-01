"""Application entrypoint ≈ Program.cs.

The lifespan handler creates tables on startup (fine for a demo; in a real
project you'd use Alembic migrations, the SQLAlchemy equivalent of EF
Migrations). Run it with:  uvicorn app.main:app --reload
Then open http://127.0.0.1:8000/docs for auto-generated Swagger UI.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request  # type: ignore[import]
from fastapi.responses import JSONResponse

from .database import Base, engine
from .models import InvalidTransition
from .routers import assets, inspections, maintenance_jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Water Asset System", version="0.1.0", lifespan=lifespan)


@app.exception_handler(InvalidTransition)
async def invalid_transition_handler(request: Request, exc: InvalidTransition) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


app.include_router(assets.router)
app.include_router(inspections.router)
app.include_router(maintenance_jobs.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
