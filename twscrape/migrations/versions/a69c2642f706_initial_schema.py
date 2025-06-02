"""initial schema

Revision ID: a69c2642f706
Revises:
Create Date: 2025-06-01 22:26:40.834871
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg


# revision identifiers, used by Alembic.
revision: str = "a69c2642f706"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to the initial Postgres layout."""

    # Ensure CITEXT extension is available (needed for case‑insensitive usernames/emails)
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    # ------------------------------------------------------------------ #
    # accounts table
    # ------------------------------------------------------------------ #
    op.create_table(
        "accounts",
        sa.Column("username", pg.CITEXT(), primary_key=True),
        sa.Column("password", sa.Text(), nullable=False),
        sa.Column("email", pg.CITEXT(), nullable=False),
        sa.Column("email_password", sa.Text(), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=False),
        sa.Column("proxy", sa.Text(), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "locks",
            pg.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "headers",
            pg.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "cookies",
            pg.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "stats",
            pg.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column(
            "last_used",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column("tx", sa.Text(), nullable=True),
        sa.Column("mfa_code", sa.Text(), nullable=True),
    )

    # Optional: Create an index to quickly find idle accounts
    op.create_index(
        "ix_accounts_active_last_used",
        "accounts",
        ["active", "last_used"],
    )


def downgrade() -> None:
    """Revert to a pristine database (drop all created objects)."""
    op.drop_index("ix_accounts_active_last_used", table_name="accounts")
    op.drop_table("accounts")
    # CITEXT is shared—only drop if you're sure nothing else uses it.
    op.execute("DROP EXTENSION IF EXISTS citext")
