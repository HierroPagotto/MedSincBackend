"""Notificações do marketplace (falhas de e-mail não quebram o fluxo)."""

from app.models.doctor import Doctor
from app.models.hospital_staff import HospitalStaff
from app.models.notification import (
    TYPE_APPLICATION_APPROVED,
    TYPE_APPLICATION_REJECTED,
    TYPE_NEW_APPLICATION,
)
from app.models.shift_opportunity import ShiftOpportunity
from app.models.user import User
from app.database import db
from app.services.notification_service import notification_service
from app.utils.email import (
    send_new_application_email,
    send_application_approved_email,
    send_application_rejected_email,
)
from app.utils.security import STAFF_ADMIN


def _fmt_date(value) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _fmt_time(value) -> str:
    text = value.isoformat() if hasattr(value, "isoformat") else str(value)
    return text[:5]


def notify_hospital_new_application(
    *, opportunity: ShiftOpportunity, doctor: Doctor
) -> None:
    hospital = opportunity.hospital
    hospital_name = hospital.name if hospital else "Hospital"
    staff_list = (
        db.session.query(HospitalStaff)
        .join(User, User.id == HospitalStaff.user_id)
        .filter(
            HospitalStaff.hospital_id == opportunity.hospital_id,
            User.is_active.is_(True),
            HospitalStaff.staff_role == STAFF_ADMIN,
        )
        .all()
    )
    if not staff_list:
        staff_list = (
            db.session.query(HospitalStaff)
            .join(User, User.id == HospitalStaff.user_id)
            .filter(
                HospitalStaff.hospital_id == opportunity.hospital_id,
                User.is_active.is_(True),
            )
            .all()
        )

    for staff in staff_list:
        email = staff.user.email if staff.user else None
        if not email:
            continue
        if not notification_service.email_allowed(
            db.session, staff.user_id, TYPE_NEW_APPLICATION
        ):
            continue
        send_new_application_email(
            to_email=email,
            staff_name=staff.name,
            doctor_name=doctor.name,
            hospital_name=hospital_name,
            opportunity_date=_fmt_date(opportunity.date),
            specialty=opportunity.specialty,
        )


def notify_doctor_application_result(
    *,
    doctor: Doctor,
    opportunity: ShiftOpportunity,
    approved: bool,
) -> None:
    hospital_name = opportunity.hospital.name if opportunity.hospital else "Hospital"
    notification_type = (
        TYPE_APPLICATION_APPROVED if approved else TYPE_APPLICATION_REJECTED
    )
    if doctor.user_id and not notification_service.email_allowed(
        db.session, doctor.user_id, notification_type
    ):
        return
    if approved:
        send_application_approved_email(
            to_email=doctor.email,
            doctor_name=doctor.name,
            hospital_name=hospital_name,
            opportunity_date=_fmt_date(opportunity.date),
            start_time=_fmt_time(opportunity.start_time),
            end_time=_fmt_time(opportunity.end_time),
            specialty=opportunity.specialty,
            payment_date=_fmt_date(opportunity.payment_date)
            if opportunity.payment_date
            else None,
        )
    else:
        send_application_rejected_email(
            to_email=doctor.email,
            doctor_name=doctor.name,
            hospital_name=hospital_name,
            opportunity_date=_fmt_date(opportunity.date),
            specialty=opportunity.specialty,
        )
