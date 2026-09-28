"""Add patients, attendances and shift_type

Revision ID: patients_attendances_v1
Revises: personal_expense_meta_v1
Create Date: 2026-09-28 10:30:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "patients_attendances_v1"
down_revision = "personal_expense_meta_v1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "doctor_id",
            sa.Integer(),
            sa.ForeignKey("doctors.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("health_plan", sa.String(100), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "attendances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "doctor_id",
            sa.Integer(),
            sa.ForeignKey("doctors.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "patient_id",
            sa.Integer(),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "shift_id",
            sa.Integer(),
            sa.ForeignKey("shifts.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("kind", sa.String(20), nullable=False, server_default="shift"),
        sa.Column("attendance_number", sa.String(50), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(10, 2), nullable=True),
        sa.Column("payment_status", sa.String(20), nullable=True),
        sa.Column("location", sa.String(150), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    with op.batch_alter_table("shifts") as batch_op:
        batch_op.add_column(sa.Column("shift_type", sa.String(30), nullable=True))


def downgrade():
    with op.batch_alter_table("shifts") as batch_op:
        batch_op.drop_column("shift_type")
    op.drop_table("attendances")
    op.drop_table("patients")
