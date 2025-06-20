"""Add faucet_request table

Revision ID: 000000000057
Revises: 000000000056
Create Date: 2025-03-03 13:36:24.237064

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "000000000057"
down_revision = "000000000056"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "faucet_request",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_profile_id", sa.UUID(), nullable=False),
        sa.Column("chain", sa.String(), nullable=False),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("transaction_signature", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_profile_id"],
            ["user_profile.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_faucet_address_time",
        "faucet_request",
        ["address", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_faucet_user_time",
        "faucet_request",
        ["user_profile_id", "created_at"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("idx_faucet_user_time", table_name="faucet_request")
    op.drop_index("idx_faucet_address_time", table_name="faucet_request")
    op.drop_table("faucet_request")
    # ### end Alembic commands ###
