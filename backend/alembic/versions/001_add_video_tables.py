"""add video tables

Revision ID: 001
Revises: 
Create Date: 2025-04-03 03:23:30.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create capture_sessions table
    op.create_table(
        'capture_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_capture_sessions_id'), 'capture_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_capture_sessions_status'), 'capture_sessions', ['status'], unique=False)

    # Create video_clips table
    op.create_table(
        'video_clips',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('storage_path', sa.String(), nullable=True),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('capture_session_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['capture_session_id'], ['capture_sessions.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_clips_id'), 'video_clips', ['id'], unique=False)
    op.create_index(op.f('ix_video_clips_status'), 'video_clips', ['status'], unique=False)
    op.create_index(op.f('ix_video_clips_title'), 'video_clips', ['title'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_video_clips_title'), table_name='video_clips')
    op.drop_index(op.f('ix_video_clips_status'), table_name='video_clips')
    op.drop_index(op.f('ix_video_clips_id'), table_name='video_clips')
    op.drop_table('video_clips')
    
    op.drop_index(op.f('ix_capture_sessions_status'), table_name='capture_sessions')
    op.drop_index(op.f('ix_capture_sessions_id'), table_name='capture_sessions')
    op.drop_table('capture_sessions')
