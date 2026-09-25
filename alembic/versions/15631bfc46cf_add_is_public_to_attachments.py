"""add is_public to attachments

Revision ID: 15631bfc46cf
Revises: 477cbe2ee3df
Create Date: 2026-09-25 09:51:05.698476

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15631bfc46cf'
down_revision: Union[str, Sequence[str], None] = '477cbe2ee3df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('attachments', sa.Column('is_public', sa.Boolean(), server_default=sa.text('false'), nullable=False))


def downgrade() -> None:
    op.drop_column('attachments', 'is_public')
