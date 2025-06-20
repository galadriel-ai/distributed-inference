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
revision = "000000000031"
down_revision = "000000000030"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "usage_limit",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "usage_tier_id",
            sa.UUID(),
            server_default=FREE_TIER_UUID,
            nullable=False,
        ),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("max_tokens_per_minute", sa.Integer(), nullable=True),
        sa.Column("max_tokens_per_day", sa.Integer(), nullable=True),
        sa.Column("max_requests_per_minute", sa.Integer(), nullable=True),
        sa.Column("max_requests_per_day", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["usage_tier_id"],
            ["usage_tier.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.drop_column("usage_tier", "max_requests_per_day")
    op.drop_column("usage_tier", "max_tokens_per_day")
    op.drop_column("usage_tier", "max_requests_per_minute")
    op.drop_column("usage_tier", "max_tokens_per_minute")

    op.execute(
        f"""
        INSERT INTO usage_limit (id, usage_tier_id, model_name, max_tokens_per_minute, max_tokens_per_day, max_requests_per_minute, max_requests_per_day, created_at, last_updated_at)
        VALUES ('{uuid7()}', '{FREE_TIER_UUID}', 'neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8', 40000, 5000000, 60, 28800, '{datetime.datetime.now(datetime.UTC)}', '{datetime.datetime.now(datetime.UTC)}');
        """
    )
    op.execute(
        f"""
        INSERT INTO usage_limit (id, usage_tier_id, model_name, max_tokens_per_minute, max_tokens_per_day, max_requests_per_minute, max_requests_per_day, created_at, last_updated_at)
        VALUES ('{uuid7()}', '{FREE_TIER_UUID}', 'neuralmagic/Meta-Llama-3.1-70B-Instruct-quantized.w4a16', 40000, 5000000, 60, 28800, '{datetime.datetime.now(datetime.UTC)}', '{datetime.datetime.now(datetime.UTC)}');
        """
    )
    op.execute(
        f"""
        INSERT INTO usage_limit (id, usage_tier_id, model_name, max_tokens_per_minute, max_tokens_per_day, max_requests_per_minute, max_requests_per_day, created_at, last_updated_at)
        VALUES ('{uuid7()}', '{FREE_TIER_UUID}', 'neuralmagic/Meta-Llama-3.1-405B-Instruct-quantized.w4a16', 40000, 1000000, 12, 6000, '{datetime.datetime.now(datetime.UTC)}', '{datetime.datetime.now(datetime.UTC)}');
        """
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "usage_tier",
        sa.Column(
            "max_tokens_per_minute", sa.INTEGER(), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "usage_tier",
        sa.Column(
            "max_requests_per_minute", sa.INTEGER(), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "usage_tier",
        sa.Column(
            "max_tokens_per_day", sa.INTEGER(), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "usage_tier",
        sa.Column(
            "max_requests_per_day", sa.INTEGER(), autoincrement=False, nullable=True
        ),
    )
    op.execute(
        f"""
        UPDATE usage_tier 
        SET 
            max_tokens_per_minute = 40000,
            max_requests_per_minute = 1000000,
            max_tokens_per_day = 60,
            max_requests_per_day = 28800
        WHERE name = 'Free Tier';
        """
    )
    op.drop_table("usage_limit")
    # ### end Alembic commands ###
