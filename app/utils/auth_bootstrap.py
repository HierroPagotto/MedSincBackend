"""Bootstrap schema: auth (Phase 0) + marketplace (Phase 1).

Idempotente sob race de múltiplos workers Gunicorn (create_all / ALTER).
"""

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.database import db
from app.models.user import User
from app.models.doctor import Doctor
from app.utils.security import ROLE_DOCTOR, ROLE_PLATFORM_ADMIN

_IGNORABLE_MYSQL_CODES = {1050, 1060, 1061, 1826}


def _mysql_error_code(exc: BaseException) -> int | None:
    orig = getattr(exc, "orig", None)
    if orig is None:
        return None
    args = getattr(orig, "args", None)
    if not args:
        return None
    try:
        return int(args[0])
    except (TypeError, ValueError):
        return None


def _is_ignorable_schema_error(exc: BaseException) -> bool:
    code = _mysql_error_code(exc)
    if code in _IGNORABLE_MYSQL_CODES:
        return True
    message = str(exc).lower()
    return any(
        needle in message
        for needle in (
            "already exists",
            "duplicate column",
            "duplicate key",
            "duplicate foreign key",
        )
    )


def _column_names(table: str) -> set[str]:
    inspector = inspect(db.engine)
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def _add_column_if_missing(table: str, column: str, ddl: str) -> None:
    if column in _column_names(table):
        return
    try:
        db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
        db.session.commit()
    except (OperationalError, ProgrammingError) as exc:
        db.session.rollback()
        if not _is_ignorable_schema_error(exc):
            raise


def _create_all_safe() -> None:
    try:
        db.create_all()
    except (OperationalError, ProgrammingError) as exc:
        db.session.rollback()
        if not _is_ignorable_schema_error(exc):
            raise
        try:
            db.create_all()
        except (OperationalError, ProgrammingError) as retry_exc:
            db.session.rollback()
            if not _is_ignorable_schema_error(retry_exc):
                raise


def _run_ddl_ignore_exists(sql: str) -> None:
    try:
        db.session.execute(text(sql))
        db.session.commit()
    except Exception:
        db.session.rollback()


def _acquire_bootstrap_lock() -> bool:
    """Evita dois workers migrando ao mesmo tempo (MySQL GET_LOCK)."""
    try:
        result = db.session.execute(
            text("SELECT GET_LOCK('medsinc_schema_bootstrap', 30)")
        ).scalar()
        return result == 1
    except Exception:
        db.session.rollback()
        return True


def _release_bootstrap_lock() -> None:
    try:
        db.session.execute(text("SELECT RELEASE_LOCK('medsinc_schema_bootstrap')"))
        db.session.commit()
    except Exception:
        db.session.rollback()


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
        Notification,
        NotificationPreference,
    )

    locked = _acquire_bootstrap_lock()
    try:
        _create_all_safe()

        _add_column_if_missing("doctors", "user_id", "user_id INT NULL")

        _add_column_if_missing("hospitals", "city", "city VARCHAR(100) NULL")
        _add_column_if_missing("hospitals", "state", "state VARCHAR(2) NULL")
        _add_column_if_missing("hospitals", "cnpj", "cnpj VARCHAR(20) NULL")
        _add_column_if_missing(
            "hospitals", "is_verified", "is_verified BOOLEAN DEFAULT 0"
        )

        _add_column_if_missing(
            "shifts", "source", "source VARCHAR(20) NOT NULL DEFAULT 'manual'"
        )
        _add_column_if_missing("shifts", "opportunity_id", "opportunity_id INT NULL")
        _add_column_if_missing(
            "shift_opportunities", "payment_date", "payment_date DATE NULL"
        )

        _run_ddl_ignore_exists(
            "CREATE UNIQUE INDEX ix_doctors_user_id ON doctors (user_id)"
        )
        _run_ddl_ignore_exists(
            "ALTER TABLE doctors ADD CONSTRAINT fk_doctors_user_id "
            "FOREIGN KEY (user_id) REFERENCES users(id)"
        )
        _run_ddl_ignore_exists(
            "CREATE INDEX ix_shifts_opportunity_id ON shifts (opportunity_id)"
        )
        _run_ddl_ignore_exists(
            "ALTER TABLE shifts ADD CONSTRAINT fk_shifts_opportunity_id "
            "FOREIGN KEY (opportunity_id) REFERENCES shift_opportunities(id)"
        )

        backfill_doctor_users()
    finally:
        if locked:
            _release_bootstrap_lock()


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
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            return
