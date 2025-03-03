"""Adds Mock Galadriel Node to be used when doing inference using 3rd party

Revision ID: 000000000032
Revises: 000000000031
Create Date: 2024-10-23 11:35:54.849570

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "000000000032"
down_revision = "000000000031"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
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
