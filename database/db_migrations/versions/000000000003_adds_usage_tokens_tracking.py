"""Adds usage tokens tracking

Revision ID: 000000000003
Revises: 000000000002
Create Date: 2024-08-29 10:25:03.245311

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "000000000003"
down_revision = "000000000002"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "usage_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("consumer_user_profile_id", sa.UUID(), nullable=False),
        sa.Column("producer_user_profile_id", sa.UUID(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["consumer_user_profile_id"],
            ["user_profile.id"],
        ),
        sa.ForeignKeyConstraint(
            ["producer_user_profile_id"],
            ["user_profile.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usage_tokens_id"), "usage_tokens", ["id"], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_usage_tokens_id"), table_name="usage_tokens")
    op.drop_table("usage_tokens")
    # ### end Alembic commands ###
