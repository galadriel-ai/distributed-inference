"""Add connected_host in NodeMetrics

Revision ID: 000000000046
Revises: 000000000045
Create Date: 2024-12-06 13:40:23.629346

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '000000000046'
down_revision = '000000000045'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "CREATE TYPE backendhost AS ENUM ('DISTRIBUTED_INFERENCE_EU', 'DISTRIBUTED_INFERENCE_US')"
    )
    op.add_column('node_metrics', sa.Column('connected_host', sa.Enum('DISTRIBUTED_INFERENCE_EU', 'DISTRIBUTED_INFERENCE_US', name='backendhost'), nullable=True))
    op.execute("UPDATE node_metrics SET connected_host=null;")



def downgrade():
    op.drop_column('node_metrics', 'connected_host')
    op.execute("DROP TYPE backendhost")
