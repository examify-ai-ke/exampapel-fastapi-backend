"""add_cascade_delete_to_answer_votes

Revision ID: b9143133af06
Revises: 2d33f2d3a351
Create Date: 2026-01-15 00:03:49.479207

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
import sqlmodel # added


# revision identifiers, used by Alembic.
revision = 'b9143133af06'
down_revision = '2d33f2d3a351'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm") 
    pass


def downgrade():
    pass
