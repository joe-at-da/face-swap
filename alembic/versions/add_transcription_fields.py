"""Add transcription fields to capture_sessions

Revision ID: add_transcription_fields
Revises: 002_add_parliament_tables
Create Date: 2025-05-08 16:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_transcription_fields'
down_revision = '002_add_parliament_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Add transcription-related fields to capture_sessions table
    op.add_column('capture_sessions', sa.Column('transcription_status', sa.String(50), nullable=True))
    op.add_column('capture_sessions', sa.Column('transcription_path', sa.String(255), nullable=True))
    op.add_column('capture_sessions', sa.Column('transcription_error', sa.Text(), nullable=True))
    op.add_column('capture_sessions', sa.Column('transcription_completed_at', sa.DateTime(), nullable=True))
    op.add_column('capture_sessions', sa.Column('transcription_results', sa.Text(), nullable=True))
    
    # Create index for transcription_status
    op.create_index(op.f('ix_capture_sessions_transcription_status'), 'capture_sessions', ['transcription_status'], unique=False)


def downgrade():
    # Drop transcription-related fields from capture_sessions table
    op.drop_index(op.f('ix_capture_sessions_transcription_status'), table_name='capture_sessions')
    op.drop_column('capture_sessions', 'transcription_results')
    op.drop_column('capture_sessions', 'transcription_completed_at')
    op.drop_column('capture_sessions', 'transcription_error')
    op.drop_column('capture_sessions', 'transcription_path')
    op.drop_column('capture_sessions', 'transcription_status')
