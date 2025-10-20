"""add note metadata fields

Revision ID: 0001_add_note_metadata_fields
Revises: 
Create Date: 2025-10-18 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_add_note_metadata_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add columns to note table
    with op.batch_alter_table('note') as batch_op:
        batch_op.add_column(sa.Column('tags', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('event_date', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('start_time', sa.Time(), nullable=True))


def downgrade():
    # Remove columns from note table
    with op.batch_alter_table('note') as batch_op:
        batch_op.drop_column('start_time')
        batch_op.drop_column('event_date')
        batch_op.drop_column('tags')
