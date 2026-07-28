"""Add results column to searches

Revision ID: a3d5f7b9c1e2
Revises: e2f3a4b5c6d7
Create Date: 2026-07-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3d5f7b9c1e2'
down_revision = 'e2f3a4b5c6d7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'searches',
        sa.Column('results', sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('searches', 'results')
