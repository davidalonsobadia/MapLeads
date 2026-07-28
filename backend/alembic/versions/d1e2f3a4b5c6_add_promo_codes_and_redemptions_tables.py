"""Add promo_codes and promo_code_redemptions tables

Revision ID: d1e2f3a4b5c6
Revises: a4b5c6d7e8f9
Create Date: 2026-07-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1e2f3a4b5c6'
down_revision = 'a4b5c6d7e8f9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('promo_codes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(), nullable=False),
    sa.Column('discount_type', sa.String(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=True),
    sa.Column('target_plan', sa.String(), nullable=True),
    sa.Column('max_uses', sa.Integer(), nullable=False),
    sa.Column('used_count', sa.Integer(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.CheckConstraint(
        "discount_type IN "
        "('percentage', 'fixed_amount', 'free_months', 'lifetime_free')",
        name='ck_promo_codes_discount_type',
    ),
    sa.CheckConstraint(
        "target_plan IS NULL OR "
        "target_plan IN ('basic', 'pro', 'enterprise')",
        name='ck_promo_codes_target_plan',
    ),
    )
    op.create_index(op.f('ix_promo_codes_id'), 'promo_codes', ['id'], unique=False)
    op.create_index(op.f('ix_promo_codes_code'), 'promo_codes', ['code'], unique=True)

    op.create_table('promo_code_redemptions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('promo_code_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('redeemed_at', sa.DateTime(), nullable=False),
    sa.Column('stripe_coupon_id', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['promo_code_id'], ['promo_codes.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint(
        'promo_code_id', 'user_id',
        name='uq_promo_code_redemptions_code_user',
    ),
    )
    op.create_index(
        op.f('ix_promo_code_redemptions_id'),
        'promo_code_redemptions', ['id'], unique=False,
    )
    op.create_index(
        op.f('ix_promo_code_redemptions_promo_code_id'),
        'promo_code_redemptions', ['promo_code_id'], unique=False,
    )
    op.create_index(
        op.f('ix_promo_code_redemptions_user_id'),
        'promo_code_redemptions', ['user_id'], unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_promo_code_redemptions_user_id'),
        table_name='promo_code_redemptions',
    )
    op.drop_index(
        op.f('ix_promo_code_redemptions_promo_code_id'),
        table_name='promo_code_redemptions',
    )
    op.drop_index(
        op.f('ix_promo_code_redemptions_id'),
        table_name='promo_code_redemptions',
    )
    op.drop_table('promo_code_redemptions')
    op.drop_index(op.f('ix_promo_codes_code'), table_name='promo_codes')
    op.drop_index(op.f('ix_promo_codes_id'), table_name='promo_codes')
    op.drop_table('promo_codes')
