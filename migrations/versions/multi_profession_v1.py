"""Add profession/council and multi specialty/practice areas

Revision ID: multi_profession_v1
Revises: update_doctor_table_v2
Create Date: 2026-03-10 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "multi_profession_v1"
down_revision = "update_doctor_table_v2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "doctors",
        sa.Column("profession", sa.String(40), nullable=False, server_default="doctor"),
    )
    op.add_column("doctors", sa.Column("council_type", sa.String(20), nullable=True))
    op.add_column("doctors", sa.Column("council_number", sa.String(20), nullable=True))
    op.add_column("doctors", sa.Column("council_state", sa.String(2), nullable=True))

    op.add_column(
        "shift_opportunities",
        sa.Column(
            "required_profession",
            sa.String(40),
            nullable=False,
            server_default="doctor",
        ),
    )

    op.create_table(
        "doctor_specialties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "doctor_id",
            sa.Integer(),
            sa.ForeignKey("doctors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("specialty", sa.String(100), nullable=False),
        sa.UniqueConstraint("doctor_id", "specialty", name="uq_doctor_specialty"),
    )
    op.create_table(
        "doctor_practice_areas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "doctor_id",
            sa.Integer(),
            sa.ForeignKey("doctors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("area", sa.String(100), nullable=False),
        sa.UniqueConstraint("doctor_id", "area", name="uq_doctor_practice_area"),
    )

    op.execute("""
        UPDATE doctors
        SET profession = 'doctor',
            council_type = COALESCE(council_type, 'CRM'),
            council_number = COALESCE(council_number, crm),
            council_state = COALESCE(council_state, crm_state)
        """)
    op.execute("""
        UPDATE shift_opportunities
        SET required_profession = 'doctor'
        WHERE required_profession IS NULL OR required_profession = ''
        """)
    op.execute("""
        INSERT INTO doctor_specialties (doctor_id, specialty)
        SELECT id, main_specialty FROM doctors
        WHERE main_specialty IS NOT NULL AND TRIM(main_specialty) <> ''
        """)


def downgrade():
    op.drop_table("doctor_practice_areas")
    op.drop_table("doctor_specialties")
    op.drop_column("shift_opportunities", "required_profession")
    op.drop_column("doctors", "council_state")
    op.drop_column("doctors", "council_number")
    op.drop_column("doctors", "council_type")
    op.drop_column("doctors", "profession")
