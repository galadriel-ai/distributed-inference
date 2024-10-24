"""Add usage_limit table that references usage_tier

Revision ID: 000000000031
Revises: 000000000030
Create Date: 2024-10-23 11:35:54.849570

"""

import datetime

from alembic import op
import sqlalchemy as sa
from uuid_extensions import uuid7

from database import FREE_TIER_UUID

# revision identifiers, used by Alembic.
revision = "000000000032"
down_revision = "000000000031"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        f"""
INSERT INTO user_profile (
    id,
    name,
    email,
    is_password_set,
    created_at,
    last_updated_at
) VALUES (
    '00000000-0000-0000-0000-000000000000',
    'Galadriel',
    'galadriel@galadriel.com',
    false,
    NOW(),
    NOW()
);

INSERT INTO node_info (
    id,
    user_profile_id,
    name,
    name_alias,
    created_at,
    last_updated_at
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000000',
    'Galadriel',
    'Galadriel',
    NOW(),
    NOW()
);

"""
    )


def downgrade():
    # TODO:
    # ### end Alembic commands ###
    pass
