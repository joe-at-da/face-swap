"""change_error_message_to_text

Revision ID: change_error_message_to_text
Revises: 9fa594727982
Create Date: 2025-07-10 01:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'change_error_message_to_text'
down_revision = '9fa594727982'
branch_labels = None
depends_on = None


def upgrade():
    # Change error_message column type from VARCHAR(255) to TEXT
    op.alter_column('capture_sessions', 'error_message',
               existing_type=sa.VARCHAR(length=255),
               type_=sa.Text(),
               existing_nullable=True)


def downgrade():
    # Change error_message column type back from TEXT to VARCHAR(255)
    op.alter_column('capture_sessions', 'error_message',
               existing_type=sa.Text(),
               type_=sa.VARCHAR(length=255),
               existing_nullable=True)
