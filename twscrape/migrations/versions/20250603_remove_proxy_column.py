"""remove proxy column from accounts

Revision ID: 20250603
Revises: 20250602
Create Date: 2025-06-02 01:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250603"
down_revision: Union[str, None] = "20250602"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("accounts", "proxy")


def downgrade() -> None:
    op.add_column("accounts", sa.Column("proxy", sa.Text(), nullable=True))
