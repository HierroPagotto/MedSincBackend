"""Exclusão e exportação de conta do titular (LGPD)."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.doctor import Doctor
from app.models.doctor_specialty import DoctorSpecialty, DoctorPracticeArea
from app.models.financial_goal import FinancialGoal
from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference
from app.models.opportunity_application import OpportunityApplication
from app.models.payment import Payment
from app.models.personal_expense import PersonalExpense
from app.models.shift import Shift
from app.models.shift_expense import ShiftExpense
from app.models.user import User
from app.models.expense_payment_method import ExpensePaymentMethod


def delete_doctor_account(db: Session, doctor: Doctor) -> None:
    """Remove médico e dados vinculados (hard delete)."""
    doctor_id = doctor.id
    linked_user_id = doctor.user_id

    db.query(OpportunityApplication).filter_by(doctor_id=doctor_id).delete(
        synchronize_session=False
    )
    db.query(FinancialGoal).filter_by(user_id=doctor_id).delete(
        synchronize_session=False
    )
    db.query(DoctorSpecialty).filter_by(doctor_id=doctor_id).delete(
        synchronize_session=False
    )
    db.query(DoctorPracticeArea).filter_by(doctor_id=doctor_id).delete(
        synchronize_session=False
    )

    shift_ids = [
        row.id for row in db.query(Shift.id).filter_by(doctor_id=doctor_id).all()
    ]
    if shift_ids:
        db.query(ShiftExpense).filter(ShiftExpense.shift_id.in_(shift_ids)).delete(
            synchronize_session=False
        )
        db.query(Payment).filter(Payment.shift_id.in_(shift_ids)).delete(
            synchronize_session=False
        )
        db.query(Shift).filter(Shift.id.in_(shift_ids)).delete(
            synchronize_session=False
        )

    db.query(PersonalExpense).filter_by(doctor_id=doctor_id).delete(
        synchronize_session=False
    )
    db.query(ExpensePaymentMethod).filter_by(doctor_id=doctor_id).delete(
        synchronize_session=False
    )

    db.delete(doctor)
    db.flush()

    if linked_user_id:
        db.query(NotificationPreference).filter_by(user_id=linked_user_id).delete(
            synchronize_session=False
        )
        db.query(Notification).filter_by(user_id=linked_user_id).delete(
            synchronize_session=False
        )
        user = db.query(User).filter(User.id == linked_user_id).first()
        if user:
            db.delete(user)

    db.commit()


def export_doctor_data(db: Session, doctor: Doctor) -> dict:
    """Portabilidade: pacote JSON com dados do titular."""
    from sqlalchemy.orm import joinedload

    shifts = (
        db.query(Shift)
        .options(joinedload(Shift.expenses), joinedload(Shift.hospital))
        .filter(Shift.doctor_id == doctor.id)
        .all()
    )
    personal = (
        db.query(PersonalExpense)
        .options(joinedload(PersonalExpense.payment_method))
        .filter(PersonalExpense.doctor_id == doctor.id)
        .all()
    )
    goals = db.query(FinancialGoal).filter(FinancialGoal.user_id == doctor.id).all()
    applications = (
        db.query(OpportunityApplication)
        .filter(OpportunityApplication.doctor_id == doctor.id)
        .all()
    )

    prefs = None
    if doctor.user_id:
        prefs = (
            db.query(NotificationPreference)
            .filter(NotificationPreference.user_id == doctor.user_id)
            .first()
        )

    return {
        "exported_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "profile": doctor.to_dict(include_shifts_count=True),
        "shifts": [s.to_dict() for s in shifts],
        "personal_expenses": [e.to_dict() for e in personal],
        "financial_goals": [
            {
                "year": g.year,
                "month": g.month,
                "value": float(g.value) if g.value is not None else None,
            }
            for g in goals
        ],
        "opportunity_applications": [
            {
                "id": a.id,
                "opportunity_id": a.opportunity_id,
                "status": a.status,
                "message": a.message,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in applications
        ],
        "notification_preferences": prefs.to_dict() if prefs else None,
    }
