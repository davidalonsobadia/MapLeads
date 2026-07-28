"""Add comp_until and comp_lifetime to subscriptions

Adds the two locally-granted free-access columns used by promo-code redemption
(epic #90, Task 3). ``comp_until`` is a nullable renewal-style timestamp;
``comp_lifetime`` is a non-null boolean defaulting to False.

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-07-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2f3a4b5c6d7'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'subscriptions',
        sa.Column('comp_until', sa.DateTime(), nullable=True),
    )
    # NOT NULL with a server default so existing rows are backfilled to False;
    # the ORM supplies the value on insert (mirrors the ``read_only`` /
    # ``users.language`` convention, which keeps the server default in place).
    op.add_column(
        'subscriptions',
        sa.Column(
            'comp_lifetime',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column('subscriptions', 'comp_lifetime')
    op.drop_column('subscriptions', 'comp_until')
