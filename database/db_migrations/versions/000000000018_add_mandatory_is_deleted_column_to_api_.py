"""Add mandatory is_deleted column to api_key table

Revision ID: 000000000018
Revises: 000000000017
Create Date: 2024-09-23 11:07:32.624806

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "000000000018"
down_revision = "000000000017"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "api_key",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("false"),
        ),
    )

    op.execute("UPDATE api_key SET is_deleted = false WHERE is_deleted IS NULL")

    op.alter_column(
        "api_key",
        "is_deleted",
        existing_type=sa.BOOLEAN(),
        nullable=False,
        server_default=sa.text("false"),
    )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("api_key", "is_deleted")
    # ### end Alembic commands ###
