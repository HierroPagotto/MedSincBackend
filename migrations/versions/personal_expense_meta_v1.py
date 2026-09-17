"""Add payment methods and recurrence fields for personal expenses

Revision ID: personal_expense_meta_v1
Revises: personal_expenses_v1
Create Date: 2026-09-17 16:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "personal_expense_meta_v1"
down_revision = "personal_expenses_v1"
branch_labels = None
depends_on = None

SYSTEM_METHODS = [
    ("boleto", "Boleto"),
    ("credit_card", "Cartão de crédito"),
    ("debit_card", "Cartão de débito"),
    ("pix", "Pix"),
    ("cash", "Dinheiro"),
    ("transfer", "Transferência"),
    ("other", "Outro"),
]


def upgrade():
    op.create_table(
        "expense_payment_methods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "doctor_id",
            sa.Integer(),
            sa.ForeignKey("doctors.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    methods = sa.table(
        "expense_payment_methods",
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("doctor_id", sa.Integer),
    )
    op.bulk_insert(
        methods,
        [
            {"name": name, "slug": slug, "is_active": True, "doctor_id": None}
            for slug, name in SYSTEM_METHODS
        ],
    )

    with op.batch_alter_table("personal_expenses") as batch_op:
        batch_op.add_column(
            sa.Column(
                "recurrence",
                sa.String(20),
                nullable=False,
                server_default="none",
            )
        )
        batch_op.add_column(
            sa.Column(
                "payment_method_id",
                sa.Integer(),
                sa.ForeignKey("expense_payment_methods.id", ondelete="SET NULL"),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("recurrence_group_id", sa.String(36), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "is_recurrence_origin",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "recurrence_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            )
        )
        batch_op.create_index(
            "ix_personal_expenses_payment_method_id", ["payment_method_id"]
        )
        batch_op.create_index(
            "ix_personal_expenses_recurrence_group_id", ["recurrence_group_id"]
        )


def downgrade():
    with op.batch_alter_table("personal_expenses") as batch_op:
        batch_op.drop_index("ix_personal_expenses_recurrence_group_id")
        batch_op.drop_index("ix_personal_expenses_payment_method_id")
        batch_op.drop_column("recurrence_active")
        batch_op.drop_column("is_recurrence_origin")
        batch_op.drop_column("recurrence_group_id")
        batch_op.drop_column("payment_method_id")
        batch_op.drop_column("recurrence")
    op.drop_table("expense_payment_methods")
