import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import extract, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.attendance import (
    Attendance,
    KIND_PRIVATE,
    KIND_SHIFT,
    ATTENDANCE_KINDS,
)
from app.models.patient import Patient
from app.models.shift import Shift


def parse_date(raw) -> datetime.date | None:
    if not raw:
        return None
    try:
        return datetime.datetime.strptime(str(raw)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def parse_positive_amount(raw) -> Decimal | None:
    if raw is None or raw == "":
        return None
    try:
        value = Decimal(str(raw)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return value


def clean_text(raw, max_len: int) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    return value[:max_len] or None


class PatientRepository:
    def list_for_doctor(
        self,
        db: Session,
        doctor_id: int,
        search: str | None = None,
        include_inactive: bool = False,
    ):
        query = db.query(Patient).filter(Patient.doctor_id == doctor_id)
        if not include_inactive:
            query = query.filter(Patient.active.is_(True))
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(Patient.name.ilike(term), Patient.health_plan.ilike(term))
            )
        return query.order_by(Patient.name.asc()).all()

    def attendance_counts(self, db: Session, doctor_id: int) -> dict[int, int]:
        rows = (
            db.query(Attendance.patient_id, func.count(Attendance.id))
            .filter(Attendance.doctor_id == doctor_id)
            .group_by(Attendance.patient_id)
            .all()
        )
        return {patient_id: count for patient_id, count in rows}

    def get_owned(self, db: Session, patient_id: int, doctor_id: int) -> Patient | None:
        return (
            db.query(Patient)
            .filter(Patient.id == patient_id, Patient.doctor_id == doctor_id)
            .first()
        )

    def create(self, db: Session, doctor_id: int, **fields) -> Patient:
        patient = Patient(doctor_id=doctor_id, active=True, **fields)
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return patient

    def update(self, db: Session, patient: Patient, **fields) -> Patient:
        for key, value in fields.items():
            setattr(patient, key, value)
        db.commit()
        db.refresh(patient)
        return patient

    def delete(self, db: Session, patient: Patient) -> None:
        db.query(Attendance).filter(Attendance.patient_id == patient.id).delete(
            synchronize_session=False
        )
        db.delete(patient)
        db.commit()


class AttendanceRepository:
    def _base_query(self, db: Session, doctor_id: int):
        return (
            db.query(Attendance)
            .options(
                joinedload(Attendance.patient),
                joinedload(Attendance.shift).joinedload(Shift.hospital),
            )
            .filter(Attendance.doctor_id == doctor_id)
        )

    def list(
        self,
        db: Session,
        doctor_id: int,
        patient_id: int | None = None,
        shift_id: int | None = None,
        kind: str | None = None,
        start_date: datetime.date | None = None,
        end_date: datetime.date | None = None,
    ):
        query = self._base_query(db, doctor_id)
        if patient_id:
            query = query.filter(Attendance.patient_id == patient_id)
        if shift_id:
            query = query.filter(Attendance.shift_id == shift_id)
        if kind:
            query = query.filter(Attendance.kind == kind)
        if start_date:
            query = query.filter(Attendance.date >= start_date)
        if end_date:
            query = query.filter(Attendance.date <= end_date)
        return query.order_by(Attendance.date.desc(), Attendance.id.desc()).all()

    def get_owned(
        self, db: Session, attendance_id: int, doctor_id: int
    ) -> Attendance | None:
        return (
            self._base_query(db, doctor_id)
            .filter(Attendance.id == attendance_id)
            .first()
        )

    def create(self, db: Session, doctor_id: int, **fields) -> Attendance:
        attendance = Attendance(doctor_id=doctor_id, **fields)
        db.add(attendance)
        db.commit()
        return self.get_owned(db, attendance.id, doctor_id)

    def update(self, db: Session, attendance: Attendance, **fields) -> Attendance:
        for key, value in fields.items():
            setattr(attendance, key, value)
        db.commit()
        return self.get_owned(db, attendance.id, attendance.doctor_id)

    def delete(self, db: Session, attendance: Attendance) -> None:
        db.delete(attendance)
        db.commit()


def private_revenue_by_month(
    db: Session, doctor_id: int, year: int
) -> dict[int, float]:
    rows = (
        db.query(
            extract("month", Attendance.date).label("month"),
            func.coalesce(func.sum(Attendance.value), 0).label("total"),
        )
        .filter(
            Attendance.doctor_id == doctor_id,
            Attendance.kind == KIND_PRIVATE,
            extract("year", Attendance.date) == year,
        )
        .group_by(extract("month", Attendance.date))
        .all()
    )
    return {int(r.month): float(r.total or 0) for r in rows}


def attendance_summary(db: Session, doctor_id: int, year: int) -> dict:
    rows = (
        db.query(
            extract("month", Attendance.date).label("month"),
            Attendance.kind,
            func.count(Attendance.id).label("count"),
        )
        .filter(
            Attendance.doctor_id == doctor_id,
            extract("year", Attendance.date) == year,
        )
        .group_by(extract("month", Attendance.date), Attendance.kind)
        .all()
    )
    revenue = private_revenue_by_month(db, doctor_id, year)

    monthly = []
    for month in range(1, 13):
        shift_count = sum(
            r.count for r in rows if int(r.month) == month and r.kind == KIND_SHIFT
        )
        private_count = sum(
            r.count for r in rows if int(r.month) == month and r.kind == KIND_PRIVATE
        )
        monthly.append(
            {
                "month": month,
                "shift_count": shift_count,
                "private_count": private_count,
                "private_revenue": revenue.get(month, 0.0),
            }
        )

    by_kind = [
        {
            "kind": kind,
            "label": label,
            "count": sum(r.count for r in rows if r.kind == kind),
        }
        for kind, label in ATTENDANCE_KINDS.items()
    ]

    return {
        "year": year,
        "monthly": monthly,
        "by_kind": by_kind,
        "total_count": sum(item["count"] for item in by_kind),
        "private_revenue_total": sum(revenue.values()),
    }
