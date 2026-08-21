"""add webhook registrations

Revision ID: f0a1b2c3d4e5
Revises: e7f8a9b0c1d2
Create Date: 2026-08-21 11:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql, sqlite

# revision identifiers, used by Alembic.
revision: str = 'f0a1b2c3d4e5'
down_revision: str | Sequence[str] | None = 'e7f8a9b0c1d2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _jsonb() -> sa.types.TypeEngine:
    """JSONB on Postgres, plain JSON on sqlite (tests/dev)."""
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(
        sqlite.JSON(), "sqlite"
    )


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'webhook_registrations',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('target_url', sa.String(length=512), nullable=False),
        sa.Column('events', _jsonb(), nullable=False),
        sa.Column('secret', sa.String(length=128), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_webhook_registrations_workspace_active',
        'webhook_registrations',
        ['workspace_id', 'active'],
        unique=False,
    )
    op.create_index(
        'ix_webhook_registrations_workspace_id',
        'webhook_registrations',
        ['workspace_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_webhook_registrations_workspace_id', table_name='webhook_registrations')
    op.drop_index(
        'ix_webhook_registrations_workspace_active', table_name='webhook_registrations'
    )
    op.drop_table('webhook_registrations')
