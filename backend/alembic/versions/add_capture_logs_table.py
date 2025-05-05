"""Add capture_logs table

Revision ID: add_capture_logs_table
Revises: 
Create Date: 2025-05-05 16:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = 'add_capture_logs_table'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'capture_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('capture_id', sa.Integer(), nullable=True),
        sa.Column('level', sa.String(length=50), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=func.now(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True),
        sa.ForeignKeyConstraint(['capture_id'], ['capture_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_capture_logs_id'), 'capture_logs', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_capture_logs_id'), table_name='capture_logs')
    op.drop_table('capture_logs')
