"""Add uid column to users table

Revision ID: b3c1d2e4f5a6
Revises: 1a98436792c4
Create Date: 2026-06-05 13:25:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3c1d2e4f5a6'
down_revision = '1a98436792c4'
branch_labels = None
depends_on = None


def upgrade():
    # Add uid column to users table (nullable so existing rows are unaffected)
    op.add_column('users', sa.Column('uid', sa.String(length=40), nullable=True))
    op.create_index(op.f('ix_users_uid'), 'users', ['uid'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_users_uid'), table_name='users')
    op.drop_column('users', 'uid')
