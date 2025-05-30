"""Add created_at and updated_at timestamps to character

Revision ID: 4c8b46c6f4ab
Revises: 086914fa157b
Create Date: <Timestamp> 

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '4c8b46c6f4ab'
down_revision: Union[str, None] = '086914fa157b' # Assuming this is the previous revision
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('character', sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column('character', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_index(op.f('ix_character_creator_id'), 'character', ['creator_id'], unique=False)
    op.create_index(op.f('ix_character_description'), 'character', ['description'], unique=False)
    op.add_column('conversation', sa.Column('last_interaction_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_conversation_last_interaction_at'), 'conversation', ['last_interaction_at'], unique=False)
    op.drop_constraint('message_conversation_id_fkey', 'message', type_='foreignkey')
    op.create_foreign_key(None, 'message', 'conversation', ['conversation_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'message', type_='foreignkey')
    op.create_foreign_key('message_conversation_id_fkey', 'message', 'conversation', ['conversation_id'], ['id'], ondelete='CASCADE')
    op.drop_index(op.f('ix_conversation_last_interaction_at'), table_name='conversation')
    op.drop_column('conversation', 'last_interaction_at')
    op.drop_index(op.f('ix_character_description'), table_name='character')
    op.drop_index(op.f('ix_character_creator_id'), table_name='character')
    op.drop_column('character', 'updated_at')
    op.drop_column('character', 'created_at')
    # ### end Alembic commands ### 