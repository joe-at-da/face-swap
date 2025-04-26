"""create_capture_sessions_table

Revision ID: e7cc2fdf4ae4
Revises: 9fa594727982
Create Date: 2025-04-26 20:22:13.757130

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7cc2fdf4ae4'
down_revision: Union[str, None] = '9fa594727982'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create capture_sessions table
    op.create_table(
        'capture_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_capture_sessions_id'), 'capture_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_capture_sessions_status'), 'capture_sessions', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_capture_sessions_status'), table_name='capture_sessions')
    op.drop_index(op.f('ix_capture_sessions_id'), table_name='capture_sessions')
    op.drop_table('capture_sessions')
