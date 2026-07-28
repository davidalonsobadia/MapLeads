"""Add oauth_accounts table and make user password nullable

Revision ID: a4b5c6d7e8f9
Revises: c9d0e1f2a3b4
Create Date: 2026-07-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a4b5c6d7e8f9'
down_revision = 'c9d0e1f2a3b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Batch mode keeps the ALTER COLUMN SQLite-safe as well as Postgres-safe.
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column(
            'hashed_password',
            existing_type=sa.String(),
            nullable=True,
        )

    op.create_table(
        'oauth_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('provider_account_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'], ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'provider',
            'provider_account_id',
            name='uq_oauth_accounts_provider_identity',
        ),
    )
    op.create_index(
        op.f('ix_oauth_accounts_id'), 'oauth_accounts', ['id'], unique=False,
    )
    op.create_index(
        op.f('ix_oauth_accounts_user_id'),
        'oauth_accounts',
        ['user_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_oauth_accounts_user_id'), table_name='oauth_accounts')
    op.drop_index(op.f('ix_oauth_accounts_id'), table_name='oauth_accounts')
    op.drop_table('oauth_accounts')

    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column(
            'hashed_password',
            existing_type=sa.String(),
            nullable=False,
        )
