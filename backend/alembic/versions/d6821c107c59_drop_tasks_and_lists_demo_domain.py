"""drop tasks and lists demo domain

Revision ID: d6821c107c59
Revises: d34c0a0cde34
Create Date: 2026-07-23 16:18:36.324847

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd6821c107c59'
down_revision = 'd34c0a0cde34'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # tasks references lists, so it must be dropped first.
    op.drop_index(op.f('ix_tasks_parent_task_id'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_id'), table_name='tasks')
    op.drop_table('tasks')
    sa.Enum(name='recurrenceenum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='priorityenum').drop(op.get_bind(), checkfirst=True)

    op.drop_index(op.f('ix_lists_id'), table_name='lists')
    op.drop_table('lists')


def downgrade() -> None:
    op.create_table('lists',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('color', sa.String(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lists_id'), 'lists', ['id'], unique=False)

    # Unlike add_column, create_table auto-creates the ENUM types for its own
    # enum columns (with checkfirst=False) - do not also create them manually
    # here, or the second CREATE TYPE collides with the first.
    priority_enum = sa.Enum('low', 'medium', 'high', name='priorityenum')
    recurrence_enum = sa.Enum('none', 'daily', 'weekly', 'monthly', name='recurrenceenum')
    op.create_table('tasks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('list_id', sa.Integer(), nullable=False),
    sa.Column('priority', priority_enum, nullable=True),
    sa.Column('due_date', sa.Date(), nullable=True),
    sa.Column('completed', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('recurrence', recurrence_enum, server_default='none', nullable=False),
    sa.Column('parent_task_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['list_id'], ['lists.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['parent_task_id'], ['tasks.id'], ondelete='SET NULL', name='fk_tasks_parent_task_id_tasks'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tasks_id'), 'tasks', ['id'], unique=False)
    op.create_index(op.f('ix_tasks_parent_task_id'), 'tasks', ['parent_task_id'], unique=False)

