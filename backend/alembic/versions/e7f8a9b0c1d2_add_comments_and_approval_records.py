"""add comments and approval records

Revision ID: e7f8a9b0c1d2
Revises: d1e2f3a4b5c6
Create Date: 2026-08-21 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e7f8a9b0c1d2'
down_revision: str | Sequence[str] | None = 'd1e2f3a4b5c6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'comments',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('author_user_id', sa.Uuid(), nullable=False),
        sa.Column('target_type', sa.String(length=24), nullable=False),
        sa.Column('target_id', sa.String(length=64), nullable=False),
        sa.Column('section_ref', sa.String(length=120), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('mentions', sa.String(length=512), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['author_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_comments_target', 'comments', ['target_type', 'target_id'], unique=False)
    op.create_index('ix_comments_workspace_id', 'comments', ['workspace_id'], unique=False)

    op.create_table(
        'approval_records',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('target_type', sa.String(length=24), nullable=False),
        sa.Column('target_id', sa.String(length=64), nullable=False),
        sa.Column('submitted_by', sa.Uuid(), nullable=False),
        sa.Column('approved_by', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('verdict_note', sa.Text(), nullable=True),
        sa.Column(
            'submitted_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.ForeignKeyConstraint(['submitted_by'], ['users.id']),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_approval_records_target', 'approval_records', ['target_type', 'target_id'], unique=False
    )
    op.create_index(
        'ix_approval_records_workspace_id', 'approval_records', ['workspace_id'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_approval_records_workspace_id', table_name='approval_records')
    op.drop_index('ix_approval_records_target', table_name='approval_records')
    op.drop_table('approval_records')
    op.drop_index('ix_comments_workspace_id', table_name='comments')
    op.drop_index('ix_comments_target', table_name='comments')
    op.drop_table('comments')
