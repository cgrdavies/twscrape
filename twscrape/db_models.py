"""
SQLAlchemy ORM definitions backing the Postgres storage layer.

These entities are kept separate from the high‑level Twitter dataclasses
in `twscrape/models.py` to avoid name clashes and heavy imports.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, TIMESTAMP, Text, text
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# --------------------------------------------------------------------------- #
# Declarative base with a deterministic naming convention
# --------------------------------------------------------------------------- #


class Base(DeclarativeBase):
    """Shared declarative base for all DB models."""

    from sqlalchemy import MetaData

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


# --------------------------------------------------------------------------- #
# Accounts table
# --------------------------------------------------------------------------- #


class Account(Base):
    """Twitter account credentials plus scraper runtime data."""

    __tablename__ = "accounts"

    # primary key ------------------------------------------------------------ #
    username: Mapped[str] = mapped_column(
        CITEXT,
        primary_key=True,
        doc="Twitter @username (case‑insensitive).",
    )

    # credentials ------------------------------------------------------------ #
    password: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    email_password: Mapped[str] = mapped_column(Text, nullable=False)

    # scraping settings ------------------------------------------------------ #
    user_agent: Mapped[str] = mapped_column(Text, nullable=False)

    # runtime state / metrics ------------------------------------------------ #
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    locks: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    headers: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    cookies: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    stats: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    error_msg: Mapped[str | None] = mapped_column(Text)
    last_used: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    _tx: Mapped[str | None] = mapped_column("tx", Text)
    mfa_code: Mapped[str | None] = mapped_column(Text)

    # --------------------------------------------------------------------- #
    # Handy dunder helpers
    # --------------------------------------------------------------------- #

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Account {self.username} active={self.active!r}>"


# --------------------------------------------------------------------------- #
# Proxies table
# --------------------------------------------------------------------------- #


class Proxy(Base):
    """HTTP proxy with health status."""

    __tablename__ = "proxies"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    fail_count: Mapped[int] = mapped_column(server_default=text("0"))
    last_failed: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
