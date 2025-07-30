"""Add transcription_retried field to CaptureSession

Revision ID: add_transcription_retried_field
Revises: 5865d62460d8
Create Date: 2023-11-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_transcription_retried_field'
down_revision = '5865d62460d8'  # This is the latest migration in the system
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('capture_sessions', sa.Column('transcription_retried', sa.Integer(), nullable=True, server_default='0'))


def downgrade():
    op.drop_column('capture_sessions', 'transcription_retried')
