"""Application entrypoint ≈ Program.cs.

The lifespan handler creates tables on startup (fine for a demo; in a real
project you'd use Alembic migrations, the SQLAlchemy equivalent of EF
Migrations). Run it with:  uvicorn app.main:app --reload
Then open http://127.0.0.1:8000/docs for auto-generated Swagger UI.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI  # type: ignore[import]

from .database import Base, engine
from .routers import assets, inspections


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Water Asset System", version="0.1.0", lifespan=lifespan)
app.include_router(assets.router)
app.include_router(inspections.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
