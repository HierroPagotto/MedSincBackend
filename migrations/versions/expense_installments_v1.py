"""Add installment fields to personal expenses

Revision ID: expense_installments_v1
Revises: patients_contact_v1
Create Date: 2026-10-09 11:20:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "expense_installments_v1"
down_revision = "patients_contact_v1"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("personal_expenses") as batch_op:
        batch_op.add_column(sa.Column("installment_number", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("installment_count", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("installment_group_id", sa.String(36), nullable=True)
        )
        batch_op.create_index(
            "ix_personal_expenses_installment_group_id",
            ["installment_group_id"],
        )


def downgrade():
    with op.batch_alter_table("personal_expenses") as batch_op:
        batch_op.drop_index("ix_personal_expenses_installment_group_id")
        batch_op.drop_column("installment_group_id")
        batch_op.drop_column("installment_count")
        batch_op.drop_column("installment_number")
