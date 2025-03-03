"""Adds profile_data size constraint

Revision ID: 000000000017
Revises: 000000000016
Create Date: 2024-09-18 14:47:37.666872

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "000000000017"
down_revision = "000000000016"
branch_labels = None
depends_on = None


def upgrade():
    # limit profile_data to 1024 bytes
    op.create_check_constraint(
        "profile_data_size_check_constraint",
        "user_profile",
        "octet_length(profile_data::text) <= 2048",
    )


def downgrade():
    op.drop_constraint("profile_data_size_check_constraint", "user_profile")
