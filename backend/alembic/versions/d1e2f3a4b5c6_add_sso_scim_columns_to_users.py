"""add sso/scim columns to users

Revision ID: d1e2f3a4b5c6
Revises: c985205644d4
Create Date: 2026-08-21 09:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: str | Sequence[str] | None = 'c985205644d4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users',
        sa.Column('is_sso', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )
    op.add_column(
        'users',
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'is_sso')
