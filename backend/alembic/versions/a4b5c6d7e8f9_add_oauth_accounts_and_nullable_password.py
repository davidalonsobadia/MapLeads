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
    # Make hashed_password optional so OAuth-only users (no local password) can
    # exist. Batch mode keeps the ALTER SQLite-safe as well as Postgres-safe.
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
            ['user_id'], ['users.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'provider',
            'provider_account_id',
            name='uq_oauth_accounts_provider_identity',
        ),
    )
    op.create_index(
        op.f('ix_oauth_accounts_user_id'),
        'oauth_accounts',
        ['user_id'],
        unique=False,
    )


def downgrade() -> None:
    # Restoring the NOT NULL constraint is unsafe once OAuth-only users (rows
    # with hashed_password IS NULL) exist: on Postgres SET NOT NULL raises an
    # IntegrityError. Guard first — before dropping anything — so an abort
    # leaves the schema untouched rather than half-downgraded.
    bind = op.get_bind()
    orphan_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM users WHERE hashed_password IS NULL")
    ).scalar()
    if orphan_count:
        raise RuntimeError(
            f"Cannot downgrade: {orphan_count} user(s) have no password "
            "(hashed_password IS NULL). Delete or migrate these OAuth-only "
            "users before downgrading."
        )

    op.drop_index(op.f('ix_oauth_accounts_user_id'), table_name='oauth_accounts')
    op.drop_table('oauth_accounts')

    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column(
            'hashed_password',
            existing_type=sa.String(),
            nullable=False,
        )
