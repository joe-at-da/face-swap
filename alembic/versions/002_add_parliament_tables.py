"""add parliament tables

Revision ID: 002_add_parliament_tables
Revises: ba11c0baf518
Create Date: 2025-05-01 17:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_parliament_tables'
down_revision = 'ba11c0baf518'
branch_labels = None
depends_on = None

def upgrade():
    # Create speaker_identifications table
    op.create_table(
        'speaker_identifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('capture_session_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('results', sa.JSON(), nullable=True),
        sa.Column('output_file', sa.String(), nullable=True),
        sa.Column('threshold', sa.Float(), default=0.6, nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['capture_session_id'], ['capture_sessions.id'], ),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_speaker_identifications_id'), 'speaker_identifications', ['id'], unique=False)
    op.create_index(op.f('ix_speaker_identifications_status'), 'speaker_identifications', ['status'], unique=False)

    # Create parliament_transcriptions table
    op.create_table(
        'parliament_transcriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('capture_session_id', sa.Integer(), nullable=False),
        sa.Column('speaker_identification_id', sa.Integer(), nullable=True),
        sa.Column('language', sa.String(), default='en', nullable=True),
        sa.Column('format', sa.String(), default='txt', nullable=True),
        sa.Column('model', sa.String(), default='medium', nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('output_file', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['capture_session_id'], ['capture_sessions.id'], ),
        sa.ForeignKeyConstraint(['speaker_identification_id'], ['speaker_identifications.id'], ),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_parliament_transcriptions_id'), 'parliament_transcriptions', ['id'], unique=False)
    op.create_index(op.f('ix_parliament_transcriptions_status'), 'parliament_transcriptions', ['status'], unique=False)

    # Create speakers table
    op.create_table(
        'speakers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('parliament_id', sa.String(), nullable=True),
        sa.Column('party', sa.String(), nullable=True),
        sa.Column('constituency', sa.String(), nullable=True),
        sa.Column('photo_url', sa.String(), nullable=True),
        sa.Column('face_encoding', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_speakers_id'), 'speakers', ['id'], unique=False)
    op.create_index(op.f('ix_speakers_name'), 'speakers', ['name'], unique=False)
    op.create_index(op.f('ix_speakers_parliament_id'), 'speakers', ['parliament_id'], unique=False)

    # Create speaker_appearances table
    op.create_table(
        'speaker_appearances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('speaker_id', sa.Integer(), nullable=False),
        sa.Column('identification_id', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Float(), nullable=False),
        sa.Column('end_time', sa.Float(), nullable=False),
        sa.Column('duration', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['speaker_id'], ['speakers.id'], ),
        sa.ForeignKeyConstraint(['identification_id'], ['speaker_identifications.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_speaker_appearances_id'), 'speaker_appearances', ['id'], unique=False)

    # Add relationships to existing tables
    op.add_column('capture_sessions', sa.Column('title', sa.String(), nullable=True))
    op.add_column('capture_sessions', sa.Column('description', sa.String(), nullable=True))
    op.add_column('capture_sessions', sa.Column('source_url', sa.String(), nullable=True))
    op.add_column('capture_sessions', sa.Column('file_path', sa.String(), nullable=True))
    op.add_column('capture_sessions', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('capture_sessions', sa.Column('duration', sa.Float(), nullable=True))
    op.add_column('capture_sessions', sa.Column('start_time', sa.DateTime(timezone=True), nullable=True))
    op.add_column('capture_sessions', sa.Column('end_time', sa.DateTime(timezone=True), nullable=True))
    op.add_column('capture_sessions', sa.Column('scheduled_start', sa.DateTime(timezone=True), nullable=True))
    op.add_column('capture_sessions', sa.Column('scheduled_end', sa.DateTime(timezone=True), nullable=True))
    op.add_column('capture_sessions', sa.Column('metadata', sa.JSON(), nullable=True))

def downgrade():
    # Remove added columns from capture_sessions
    op.drop_column('capture_sessions', 'metadata')
    op.drop_column('capture_sessions', 'scheduled_end')
    op.drop_column('capture_sessions', 'scheduled_start')
    op.drop_column('capture_sessions', 'end_time')
    op.drop_column('capture_sessions', 'start_time')
    op.drop_column('capture_sessions', 'duration')
    op.drop_column('capture_sessions', 'file_size')
    op.drop_column('capture_sessions', 'file_path')
    op.drop_column('capture_sessions', 'source_url')
    op.drop_column('capture_sessions', 'description')
    op.drop_column('capture_sessions', 'title')

    # Drop speaker_appearances table
    op.drop_index(op.f('ix_speaker_appearances_id'), table_name='speaker_appearances')
    op.drop_table('speaker_appearances')

    # Drop speakers table
    op.drop_index(op.f('ix_speakers_parliament_id'), table_name='speakers')
    op.drop_index(op.f('ix_speakers_name'), table_name='speakers')
    op.drop_index(op.f('ix_speakers_id'), table_name='speakers')
    op.drop_table('speakers')

    # Drop parliament_transcriptions table
    op.drop_index(op.f('ix_parliament_transcriptions_status'), table_name='parliament_transcriptions')
    op.drop_index(op.f('ix_parliament_transcriptions_id'), table_name='parliament_transcriptions')
    op.drop_table('parliament_transcriptions')

    # Drop speaker_identifications table
    op.drop_index(op.f('ix_speaker_identifications_status'), table_name='speaker_identifications')
    op.drop_index(op.f('ix_speaker_identifications_id'), table_name='speaker_identifications')
    op.drop_table('speaker_identifications')
