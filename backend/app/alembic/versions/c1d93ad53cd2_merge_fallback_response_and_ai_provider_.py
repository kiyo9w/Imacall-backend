"""Merge fallback_response and ai_provider_config branches

Revision ID: c1d93ad53cd2
Revises: e5a9c8f7b0d1, 6c48a894a48d
Create Date: 2025-05-30 00:04:22.196749

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'c1d93ad53cd2'
down_revision = ('e5a9c8f7b0d1', '6c48a894a48d')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
