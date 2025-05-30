"""Add fallback_response to Character model

Revision ID: e5a9c8f7b0d1
Revises: 47b3823eff09
Create Date: 2025-05-30 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'e5a9c8f7b0d1'
down_revision = '47b3823eff09'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('character', sa.Column('fallback_response', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('character', 'fallback_response')
    # ### end Alembic commands ### 