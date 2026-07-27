"""Add user language and updated_at columns

Revision ID: c9d0e1f2a3b4
Revises: b7c8d9e0f1a2
Create Date: 2026-07-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c9d0e1f2a3b4'
down_revision = 'b7c8d9e0f1a2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add ``language`` as NOT NULL with a server default so existing rows are
    # backfilled to 'en'; the check constraint enforces the supported set at
    # the DB layer, mirroring the subscriptions/leads convention.
    op.add_column(
        'users',
        sa.Column(
            'language',
            sa.String(length=2),
            nullable=False,
            server_default='en',
        ),
    )
    op.add_column(
        'users',
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_check_constraint(
        'ck_users_language',
        'users',
        "language IN ('en', 'es')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_users_language', 'users', type_='check')
    op.drop_column('users', 'updated_at')
    op.drop_column('users', 'language')
