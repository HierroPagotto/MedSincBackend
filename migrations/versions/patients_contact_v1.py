"""Add phone and cpf to patients

Revision ID: patients_contact_v1
Revises: patients_attendances_v1
Create Date: 2026-10-09 11:10:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "patients_contact_v1"
down_revision = "patients_attendances_v1"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("patients") as batch_op:
        batch_op.add_column(sa.Column("phone", sa.String(20), nullable=True))
        batch_op.add_column(sa.Column("cpf", sa.String(11), nullable=True))
        batch_op.create_index(
            "uq_patients_doctor_cpf", ["doctor_id", "cpf"], unique=True
        )


def downgrade():
    with op.batch_alter_table("patients") as batch_op:
        batch_op.drop_index("uq_patients_doctor_cpf")
        batch_op.drop_column("cpf")
        batch_op.drop_column("phone")
