"""Bootstrap schema: auth (Phase 0) + marketplace (Phase 1)."""

from sqlalchemy import inspect, text

from app.database import db
from app.models.user import User
from app.models.doctor import Doctor
from app.utils.security import ROLE_DOCTOR, ROLE_PLATFORM_ADMIN


def _column_names(table: str) -> set[str]:
    inspector = inspect(db.engine)
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def _add_column_if_missing(table: str, column: str, ddl: str) -> None:
    if column not in _column_names(table):
        db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
        db.session.commit()


def ensure_auth_schema() -> None:
    """Cria tabelas novas e colunas extras em bases já existentes (MySQL)."""
    from app.models import (
        User,
        HospitalStaff,
        Doctor,
        Hospital,
        Shift,
        Payment,
        FinancialGoal,
        ShiftOpportunity,
        OpportunityApplication,
    )

    db.create_all()

    _add_column_if_missing("doctors", "user_id", "user_id INT NULL")

    _add_column_if_missing("hospitals", "city", "city VARCHAR(100) NULL")
    _add_column_if_missing("hospitals", "state", "state VARCHAR(2) NULL")
    _add_column_if_missing("hospitals", "cnpj", "cnpj VARCHAR(20) NULL")
    _add_column_if_missing("hospitals", "is_verified", "is_verified BOOLEAN DEFAULT 0")

    _add_column_if_missing(
        "shifts", "source", "source VARCHAR(20) NOT NULL DEFAULT 'manual'"
    )
    _add_column_if_missing("shifts", "opportunity_id", "opportunity_id INT NULL")

    try:
        db.session.execute(
            text("CREATE UNIQUE INDEX ix_doctors_user_id ON doctors (user_id)")
        )
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        db.session.execute(
            text(
                "ALTER TABLE doctors ADD CONSTRAINT fk_doctors_user_id "
                "FOREIGN KEY (user_id) REFERENCES users(id)"
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        db.session.execute(
            text("CREATE INDEX ix_shifts_opportunity_id ON shifts (opportunity_id)")
        )
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        db.session.execute(
            text(
                "ALTER TABLE shifts ADD CONSTRAINT fk_shifts_opportunity_id "
                "FOREIGN KEY (opportunity_id) REFERENCES shift_opportunities(id)"
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()

    backfill_doctor_users()


def backfill_doctor_users() -> None:
    """Cria User para doctors sem user_id, reutilizando o hash de senha atual."""
    doctors = db.session.query(Doctor).filter(Doctor.user_id.is_(None)).all()
    for doctor in doctors:
        existing = db.session.query(User).filter(User.email == doctor.email).first()
        if existing:
            doctor.user_id = existing.id
            continue

        role = ROLE_PLATFORM_ADMIN if doctor.is_admin else ROLE_DOCTOR
        user = User(
            email=doctor.email,
            password=doctor.password,
            role=role,
            is_active=True,
        )
        db.session.add(user)
        db.session.flush()
        doctor.user_id = user.id

    if doctors:
        db.session.commit()
