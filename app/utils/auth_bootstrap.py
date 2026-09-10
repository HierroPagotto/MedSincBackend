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


def _make_doctor_signup_columns_nullable() -> None:
    """Profile fields collected after signup must accept NULL on existing DBs."""
    for ddl in (
        "ALTER TABLE doctors MODIFY COLUMN crm VARCHAR(20) NULL",
        "ALTER TABLE doctors MODIFY COLUMN crm_state VARCHAR(2) NULL",
        "ALTER TABLE doctors MODIFY COLUMN graduation_year INT NULL",
        "ALTER TABLE doctors MODIFY COLUMN city VARCHAR(100) NULL",
        "ALTER TABLE doctors MODIFY COLUMN phone VARCHAR(20) NULL",
        "ALTER TABLE doctors MODIFY COLUMN state VARCHAR(2) NULL",
    ):
        _run_ddl_ignore_exists(ddl)


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
        DoctorSpecialty,
        DoctorPracticeArea,
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

        # Allow doctor signup without full profile (CRM, city, etc.)
        _make_doctor_signup_columns_nullable()

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
        _add_column_if_missing(
            "shift_opportunities",
            "requires_acls",
            "requires_acls BOOLEAN NOT NULL DEFAULT 0",
        )
        _add_column_if_missing(
            "shift_opportunities",
            "requires_bls",
            "requires_bls BOOLEAN NOT NULL DEFAULT 0",
        )
        _add_column_if_missing(
            "shift_opportunities",
            "requires_atls",
            "requires_atls BOOLEAN NOT NULL DEFAULT 0",
        )
        _add_column_if_missing(
            "shift_opportunities",
            "requires_pals",
            "requires_pals BOOLEAN NOT NULL DEFAULT 0",
        )

        _add_column_if_missing(
            "doctors",
            "profession",
            "profession VARCHAR(40) NOT NULL DEFAULT 'doctor'",
        )
        _add_column_if_missing(
            "doctors", "council_type", "council_type VARCHAR(20) NULL"
        )
        _add_column_if_missing(
            "doctors", "council_number", "council_number VARCHAR(20) NULL"
        )
        _add_column_if_missing(
            "doctors", "council_state", "council_state VARCHAR(2) NULL"
        )
        _add_column_if_missing(
            "shift_opportunities",
            "required_profession",
            "required_profession VARCHAR(40) NOT NULL DEFAULT 'doctor'",
        )

        _run_ddl_ignore_exists(
            "CREATE INDEX ix_doctors_profession ON doctors (profession)"
        )
        _run_ddl_ignore_exists(
            "CREATE INDEX ix_shift_opportunities_required_profession "
            "ON shift_opportunities (required_profession)"
        )
        _run_ddl_ignore_exists(
            "CREATE UNIQUE INDEX uq_doctor_council "
            "ON doctors (council_type, council_number, council_state)"
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
        backfill_profession_and_council()
        backfill_opportunity_required_profession()
        backfill_doctor_specialties_from_main()
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


def backfill_profession_and_council() -> None:
    """Profissão médico + conselho CRM a partir do CRM legado; unifica técnicos legados."""
    from app.utils.professions import (
        COUNCIL_CRM,
        PROFESSION_DOCTOR,
        normalize_profession,
    )

    doctors = db.session.query(Doctor).all()
    changed = False
    for doctor in doctors:
        normalized = normalize_profession(getattr(doctor, "profession", None))
        if normalized and doctor.profession != normalized:
            doctor.profession = normalized
            changed = True
        elif not getattr(doctor, "profession", None):
            doctor.profession = PROFESSION_DOCTOR
            changed = True
        if not doctor.council_type and (doctor.crm or doctor.council_number):
            doctor.council_type = COUNCIL_CRM
            changed = True
        if not doctor.council_number and doctor.crm:
            doctor.council_number = doctor.crm
            changed = True
        if not doctor.council_state and doctor.crm_state:
            doctor.council_state = doctor.crm_state
            changed = True
    if changed:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()


def backfill_opportunity_required_profession() -> None:
    from app.models.shift_opportunity import ShiftOpportunity
    from app.utils.professions import PROFESSION_DOCTOR, normalize_profession

    rows = db.session.query(ShiftOpportunity).all()
    changed = False
    for row in rows:
        normalized = normalize_profession(row.required_profession) or PROFESSION_DOCTOR
        if not row.required_profession or row.required_profession != normalized:
            row.required_profession = normalized
            changed = True
    if changed:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()


def backfill_doctor_specialties_from_main() -> None:
    from app.models.doctor_specialty import DoctorSpecialty

    doctors = db.session.query(Doctor).all()
    changed = False
    for doctor in doctors:
        if not doctor.main_specialty:
            continue
        has_rows = (
            db.session.query(DoctorSpecialty.id)
            .filter(DoctorSpecialty.doctor_id == doctor.id)
            .first()
        )
        if has_rows:
            continue
        db.session.add(
            DoctorSpecialty(doctor_id=doctor.id, specialty=doctor.main_specialty)
        )
        changed = True
    if changed:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
