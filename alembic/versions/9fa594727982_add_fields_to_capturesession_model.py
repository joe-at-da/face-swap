"""Add fields to CaptureSession model

Revision ID: 9fa594727982
Revises: 5865d62460d8
Create Date: 2025-04-26 12:27:51.656583

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9fa594727982'
down_revision: Union[str, None] = '5865d62460d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to capture_sessions table
    op.add_column('capture_sessions', sa.Column('title', sa.String(255), nullable=True))
    op.add_column('capture_sessions', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('capture_sessions', sa.Column('source_url', sa.String(255), nullable=True))
    op.add_column('capture_sessions', sa.Column('file_path', sa.String(255), nullable=True))
    op.add_column('capture_sessions', sa.Column('file_size', sa.BigInteger(), nullable=True))
    op.add_column('capture_sessions', sa.Column('duration', sa.Integer(), nullable=True))
    op.add_column('capture_sessions', sa.Column('scheduled_start', sa.DateTime(timezone=True), nullable=True))
    op.add_column('capture_sessions', sa.Column('scheduled_end', sa.DateTime(timezone=True), nullable=True))
    op.add_column('capture_sessions', sa.Column('start_time', sa.DateTime(timezone=True), nullable=True))
    op.add_column('capture_sessions', sa.Column('end_time', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove columns from capture_sessions table
    op.drop_column('capture_sessions', 'title')
    op.drop_column('capture_sessions', 'description')
    op.drop_column('capture_sessions', 'source_url')
    op.drop_column('capture_sessions', 'file_path')
    op.drop_column('capture_sessions', 'file_size')
    op.drop_column('capture_sessions', 'duration')
    op.drop_column('capture_sessions', 'scheduled_start')
    op.drop_column('capture_sessions', 'scheduled_end')
    op.drop_column('capture_sessions', 'start_time')
    op.drop_column('capture_sessions', 'end_time')
