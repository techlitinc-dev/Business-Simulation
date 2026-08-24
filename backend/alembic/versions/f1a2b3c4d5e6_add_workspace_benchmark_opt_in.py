"""add workspace benchmark opt-in column

Revision ID: f1a2b3c4d5e6
Revises: f0a1b2c3d4e5
Create Date: 2026-08-24 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: str | Sequence[str] | None = 'f0a1b2c3d4e5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the workspace-level benchmark opt-in flag (defaults to on)."""
    op.add_column(
        'workspaces',
        sa.Column(
            'benchmark_opt_in',
            sa.Boolean(),
            server_default=sa.text('true'),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Drop the workspace benchmark opt-in flag."""
    op.drop_column('workspaces', 'benchmark_opt_in')