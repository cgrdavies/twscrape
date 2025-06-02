"""add proxy_id column to accounts

Revision ID: 20250604
Revises: 20250603
Create Date: 2025-06-02 02:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250604"
down_revision: Union[str, None] = "20250603"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("proxy_id", sa.Integer(), sa.ForeignKey("proxies.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("accounts", "proxy_id")
