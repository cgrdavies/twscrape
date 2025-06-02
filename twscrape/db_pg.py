"""
twscrape PostgreSQL database module using SQLAlchemy 2.0 async core.

This module provides database connectivity and migration checking for twscrape's
PostgreSQL backend using modern SQLAlchemy async patterns.

Environment variables
---------------------
TWSCRAPE_DATABASE_URL       e.g. postgresql+asyncpg://user:pass@host/db
TWSCRAPE_DB_POOL_SIZE       (optional) default 10
TWSCRAPE_DB_MAX_OVERFLOW    (optional) default 20
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import get_database_url

# --------------------------------------------------------------------------- #
# Engine & session factory (globals for production, can be overridden for tests)
# --------------------------------------------------------------------------- #

_engine: AsyncEngine | None = None
_session_factory = None


def create_engine(database_url: str | None = None) -> AsyncEngine:
    """Create a new async database engine."""
    url = database_url or get_database_url()
    return create_async_engine(
        url,
        pool_size=int(os.getenv("TWSCRAPE_DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("TWSCRAPE_DB_MAX_OVERFLOW", "20")),
        pool_pre_ping=True,
    )


def get_engine() -> AsyncEngine:
    """Get or create the async database engine."""
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


def set_engine(engine: AsyncEngine) -> None:
    """Set a custom engine (useful for testing)."""
    global _engine, _session_factory
    _engine = engine
    _session_factory = None  # Reset session factory


def get_session_factory():
    """Get or create the session factory."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        # expire_on_commit=False so ORM objects remain usable after commit
        _session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return _session_factory


async def dispose_engine() -> None:
    """Dispose of the current engine and reset state."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
    _engine = None
    _session_factory = None


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """
    Context manager that starts a transaction and automatically commits
    (or rolls back on error) when exiting the ``async with`` block.

    Example
    -------
    >>> async with session_scope() as session:
    ...     await session.execute(text("INSERT INTO table(col) VALUES (:v)"), {"v": 123})
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            async with session.begin():
                yield session
        except Exception:
            # make sure the transaction is rolled back before propagating
            await session.rollback()
            raise


# --------------------------------------------------------------------------- #
# Migration check helper
# --------------------------------------------------------------------------- #

_migration_checked = False
_migrations_exist = True


class MigrationError(Exception):
    """Raised when database migrations have not been run."""

    pass


async def check_migrations():
    """Check if database migrations have been run and warn if not."""
    global _migration_checked, _migrations_exist
    if _migration_checked:
        if not _migrations_exist:
            raise MigrationError(
                "Database schema not found. Please run 'alembic upgrade head' first."
            )
        return

    try:
        # Check if main tables exist
        async with session_scope() as session:
            # Check for accounts table
            result = await session.execute(
                text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'accounts'
                )
            """)
            )
            accounts_exists = result.scalar()

            if not accounts_exists:
                _migrations_exist = False
                print("⚠️  Database schema not found!")
                print("📋 Please run migrations first:")
                print("   alembic upgrade head")
                print()
                print("💡 Or set TWSCRAPE_DATABASE_URL and run:")
                print("   TWSCRAPE_DATABASE_URL='your-db-url' alembic upgrade head")
                print()
                raise MigrationError(
                    "Database schema not found. Please run 'alembic upgrade head' first."
                )

        _migration_checked = True
    except MigrationError:
        _migration_checked = True
        raise
    except Exception:
        # If we can't connect to check, that's probably a bigger issue
        # Don't spam with migration warnings in that case
        _migration_checked = True


# --------------------------------------------------------------------------- #
# Database helper functions
# --------------------------------------------------------------------------- #


async def fetchone(sql: str, params: Mapping[str, Any] | None = None):
    """
    Execute *sql* and return the first row (or ``None``).
    """
    await check_migrations()
    async with session_scope() as session:
        result = await session.execute(text(sql), params or {})
        return result.fetchone()


async def fetchall(sql: str, params: Mapping[str, Any] | None = None):
    """
    Execute *sql* and return all rows as a list.
    """
    await check_migrations()
    async with session_scope() as session:
        result = await session.execute(text(sql), params or {})
        return result.fetchall()


async def execute(
    sql: str,
    params: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
) -> None:
    """
    Execute *sql* once (or many times if *params* is a sequence).
    """
    await check_migrations()
    async with session_scope() as session:
        if isinstance(params, Sequence) and not isinstance(params, (bytes, str)):
            # executemany
            await session.execute(text(sql), params)
        else:
            await session.execute(text(sql), params or {})


async def executemany(
    sql: str,
    seq: Sequence[Mapping[str, Any]],
) -> None:
    """
    Convenience wrapper for backward compatibility.
    Simply forwards to ``execute`` with a sequence argument.
    """
    await execute(sql, seq)


# --------------------------------------------------------------------------- #
# Public exports (helps static type‑checkers)
# --------------------------------------------------------------------------- #

__all__ = [
    "get_engine",
    "session_scope",
    "execute",
    "executemany",
    "fetchone",
    "fetchall",
]
