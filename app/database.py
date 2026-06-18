"""Database wiring: async engine + session factory + dependency.

C# analogy: this file is your DbContext registration in Program.cs.
The async_sessionmaker is the factory; get_db() is what the DI container
hands to each request (like an injected DbContext per request).
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# SQLite + aiosqlite keeps the demo self-contained (no DB server to install).
# To target your MySQL practice DB instead, swap the URL for something like:
#   "mysql+asyncmy://user:pass@localhost:3306/water"  (pip install asyncmy)
DATABASE_URL = "sqlite+aiosqlite:///./water_assets.db"

engine = create_async_engine(DATABASE_URL, echo=False)

# Like a scoped DbContext factory. expire_on_commit=False so objects stay
# usable after commit (handy when returning them from an endpoint).
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base for all ORM models — the equivalent of inheriting nothing special
    in EF, but SQLAlchemy needs a shared declarative base."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency. `yield` makes this a scoped resource: FastAPI
    runs the teardown (close) after the response, like a `using` block."""
    async with SessionLocal() as session:
        yield session
