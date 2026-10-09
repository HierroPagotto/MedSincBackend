"""Add graduation university to doctors

Revision ID: doctor_university_v1
Revises: expense_installments_v1
Create Date: 2026-10-09 11:50:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "doctor_university_v1"
down_revision = "expense_installments_v1"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("doctors") as batch_op:
        batch_op.add_column(
            sa.Column("graduation_university", sa.String(150), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("doctors") as batch_op:
        batch_op.drop_column("graduation_university")
