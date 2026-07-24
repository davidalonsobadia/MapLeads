"""Add searches table

Revision ID: f2a1c3d4e5b6
Revises: e17ae294901b
Create Date: 2026-07-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2a1c3d4e5b6'
down_revision = 'e17ae294901b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('searches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('keyword', sa.String(), nullable=False),
    sa.Column('location_type', sa.String(), nullable=False),
    sa.Column('params', sa.JSON(), nullable=False),
    sa.Column('result_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.CheckConstraint(
        "location_type IN ('text', 'point')",
        name='ck_searches_location_type',
    ),
    )
    op.create_index(op.f('ix_searches_id'), 'searches', ['id'], unique=False)
    op.create_index(op.f('ix_searches_project_id'), 'searches', ['project_id'], unique=False)
    op.create_index(op.f('ix_searches_user_id'), 'searches', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_searches_user_id'), table_name='searches')
    op.drop_index(op.f('ix_searches_project_id'), table_name='searches')
    op.drop_index(op.f('ix_searches_id'), table_name='searches')
    op.drop_table('searches')
