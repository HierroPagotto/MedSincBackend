"""Add shift_expenses table

Revision ID: shift_expenses_v1
Revises: multi_profession_v1
Create Date: 2026-09-17 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "shift_expenses_v1"
down_revision = "multi_profession_v1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "shift_expenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "shift_id",
            sa.Integer(),
            sa.ForeignKey("shifts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "doctor_id",
            sa.Integer(),
            sa.ForeignKey("doctors.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table("shift_expenses")
