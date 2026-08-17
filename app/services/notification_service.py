"""Criação e consulta de notificações in-app (Fase 1)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

import pytz
from sqlalchemy import extract, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.doctor import Doctor
from app.models.financial_goal import FinancialGoal
from app.models.hospital_staff import HospitalStaff
from app.models.notification import (
    Notification,
    TYPE_APPLICATION_APPROVED,
    TYPE_APPLICATION_REJECTED,
    TYPE_GOAL_PROGRESS,
    TYPE_NEW_APPLICATION,
    TYPE_OPPORTUNITY_FILLED,
    TYPE_PAYMENT_PENDING,
    TYPE_SCHEDULE_CONFLICT,
    TYPE_SHIFT_TOMORROW,
)
from app.models.shift import Shift
from app.models.user import User
from app.utils.security import STAFF_ADMIN


def _fmt_date(value: date | None) -> str:
    if not value:
        return ""
    return value.strftime("%d/%m")


def _fmt_time(value: time | None) -> str:
    if not value:
        return ""
    return value.strftime("%H:%M")


class NotificationService:
    def create(
        self,
        session: Session,
        *,
        user_id: int,
        type: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
        dedupe_key: str | None = None,
        commit: bool = True,
    ) -> Notification | None:
        if not user_id:
            return None

        if dedupe_key:
            existing = (
                session.query(Notification)
                .filter(
                    Notification.user_id == user_id,
                    Notification.type == type,
                    Notification.dedupe_key == dedupe_key,
                )
                .first()
            )
            if existing:
                return existing

        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            data=data or {},
            dedupe_key=dedupe_key,
        )
        session.add(notification)
        if commit:
            session.commit()
            session.refresh(notification)
        else:
            session.flush()
        return notification

    def list_for_user(
        self,
        session: Session,
        user_id: int,
        *,
        page: int = 1,
        per_page: int = 20,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int]:
        query = session.query(Notification).filter(Notification.user_id == user_id)
        if unread_only:
            query = query.filter(Notification.read_at.is_(None))
        total = query.count()
        page = max(1, page)
        per_page = min(50, max(1, per_page))
        items = (
            query.order_by(Notification.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

    def unread_count(self, session: Session, user_id: int) -> int:
        return (
            session.query(func.count(Notification.id))
            .filter(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .scalar()
            or 0
        )

    def mark_read(
        self, session: Session, notification: Notification, *, commit: bool = True
    ) -> Notification:
        if notification.read_at is None:
            notification.read_at = datetime.now(pytz.UTC)
            if commit:
                session.commit()
                session.refresh(notification)
            else:
                session.flush()
        return notification

    def mark_all_read(self, session: Session, user_id: int) -> int:
        now = datetime.now(pytz.UTC)
        updated = (
            session.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .update({Notification.read_at: now}, synchronize_session=False)
        )
        session.commit()
        return int(updated or 0)

    def get_for_user(
        self, session: Session, notification_id: int, user_id: int
    ) -> Notification | None:
        return (
            session.query(Notification)
            .filter(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .first()
        )

    def notify_hospital_staff(
        self,
        session: Session,
        *,
        hospital_id: int,
        type: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
        dedupe_key_prefix: str | None = None,
        commit: bool = True,
    ) -> int:
        staff_list = (
            session.query(HospitalStaff)
            .options(joinedload(HospitalStaff.user))
            .join(User, User.id == HospitalStaff.user_id)
            .filter(
                HospitalStaff.hospital_id == hospital_id,
                User.is_active.is_(True),
                HospitalStaff.staff_role == STAFF_ADMIN,
            )
            .all()
        )
        if not staff_list:
            staff_list = (
                session.query(HospitalStaff)
                .options(joinedload(HospitalStaff.user))
                .join(User, User.id == HospitalStaff.user_id)
                .filter(
                    HospitalStaff.hospital_id == hospital_id,
                    User.is_active.is_(True),
                )
                .all()
            )

        created = 0
        for staff in staff_list:
            if not staff.user_id:
                continue
            dedupe = None
            if dedupe_key_prefix:
                dedupe = f"{dedupe_key_prefix}:staff:{staff.id}"
            result = self.create(
                session,
                user_id=staff.user_id,
                type=type,
                title=title,
                body=body,
                data=data,
                dedupe_key=dedupe,
                commit=False,
            )
            if result:
                created += 1

        if commit:
            session.commit()
        return created

    def notify_doctor_shift_tomorrow(
        self, session: Session, shift: Shift, *, commit: bool = True
    ) -> Notification | None:
        doctor = shift.doctor or session.query(Doctor).get(shift.doctor_id)
        if not doctor or not doctor.user_id:
            return None
        hospital_name = shift.hospital.name if shift.hospital else "Hospital"
        start = _fmt_time(shift.start_time)
        return self.create(
            session,
            user_id=doctor.user_id,
            type=TYPE_SHIFT_TOMORROW,
            title="Plantão amanhã",
            body=f"Seu plantão no {hospital_name} começa amanhã às {start}.",
            data={
                "shift_id": shift.id,
                "hospital_id": shift.hospital_id,
                "href": "/shifts",
            },
            dedupe_key=f"shift_tomorrow:{shift.id}:{shift.date.isoformat()}",
            commit=commit,
        )

    def notify_doctor_payment_pending(
        self, session: Session, shift: Shift, *, commit: bool = True
    ) -> Notification | None:
        doctor = shift.doctor or session.query(Doctor).get(shift.doctor_id)
        if not doctor or not doctor.user_id:
            return None
        return self.create(
            session,
            user_id=doctor.user_id,
            type=TYPE_PAYMENT_PENDING,
            title="Pagamento pendente",
            body=f"O pagamento do plantão de {_fmt_date(shift.date)} está pendente.",
            data={
                "shift_id": shift.id,
                "payment_date": (
                    shift.payment_date.isoformat() if shift.payment_date else None
                ),
                "href": "/finance",
            },
            dedupe_key=f"payment_pending:{shift.id}:{shift.payment_date}",
            commit=commit,
        )

    def notify_schedule_conflict(
        self,
        session: Session,
        *,
        doctor: Doctor,
        shift: Shift,
        conflicting: Shift,
        commit: bool = True,
    ) -> Notification | None:
        if not doctor.user_id:
            return None
        return self.create(
            session,
            user_id=doctor.user_id,
            type=TYPE_SCHEDULE_CONFLICT,
            title="Conflito de plantões",
            body="Existe conflito entre dois plantões.",
            data={
                "shift_id": shift.id,
                "conflicting_shift_id": conflicting.id,
                "href": "/shifts",
            },
            dedupe_key=f"conflict:{min(shift.id, conflicting.id)}:{max(shift.id, conflicting.id)}",
            commit=commit,
        )

    def maybe_notify_goal_progress(
        self, session: Session, doctor: Doctor, *, commit: bool = True
    ) -> list[Notification]:
        if not doctor or not doctor.user_id:
            return []

        brazil_tz = pytz.timezone("America/Sao_Paulo")
        now = datetime.now(brazil_tz)
        year, month = now.year, now.month

        goal = (
            session.query(FinancialGoal)
            .filter_by(user_id=doctor.id, year=year, month=month)
            .first()
        )
        if not goal:
            goal = (
                session.query(FinancialGoal)
                .filter_by(user_id=doctor.id, year=0, month=0)
                .first()
            )
        if not goal or not goal.value or float(goal.value) <= 0:
            return []

        earnings = (
            session.query(func.coalesce(func.sum(Shift.value), 0))
            .filter(
                Shift.doctor_id == doctor.id,
                extract("month", Shift.payment_date) == month,
                extract("year", Shift.payment_date) == year,
                Shift.status.in_(["scheduled", "completed", "paid"]),
                Shift.payment_date.isnot(None),
            )
            .scalar()
        )
        earnings = float(earnings or 0)
        target = float(goal.value)
        ratio = earnings / target if target else 0

        created: list[Notification] = []
        if ratio >= 0.8:
            n80 = self.create(
                session,
                user_id=doctor.user_id,
                type=TYPE_GOAL_PROGRESS,
                title="Meta mensal",
                body="Você atingiu 80% da sua meta mensal.",
                data={
                    "percent": 80,
                    "earnings": earnings,
                    "goal": target,
                    "year": year,
                    "month": month,
                    "href": "/finance",
                },
                dedupe_key=f"goal_80:{doctor.id}:{year}-{month:02d}",
                commit=False,
            )
            if n80:
                created.append(n80)
        if ratio >= 1.0:
            n100 = self.create(
                session,
                user_id=doctor.user_id,
                type=TYPE_GOAL_PROGRESS,
                title="Meta mensal",
                body="Você atingiu 100% da sua meta mensal.",
                data={
                    "percent": 100,
                    "earnings": earnings,
                    "goal": target,
                    "year": year,
                    "month": month,
                    "href": "/finance",
                },
                dedupe_key=f"goal_100:{doctor.id}:{year}-{month:02d}",
                commit=False,
            )
            if n100:
                created.append(n100)

        if commit:
            session.commit()
        return created

    def notify_application_result(
        self,
        session: Session,
        *,
        doctor: Doctor,
        opportunity,
        approved: bool,
        commit: bool = True,
    ) -> Notification | None:
        if not doctor.user_id:
            return None
        hospital_name = (
            opportunity.hospital.name
            if opportunity and opportunity.hospital
            else "Hospital"
        )
        if approved:
            return self.create(
                session,
                user_id=doctor.user_id,
                type=TYPE_APPLICATION_APPROVED,
                title="Candidatura aprovada",
                body=f"Sua candidatura em {hospital_name} foi aprovada.",
                data={
                    "opportunity_id": opportunity.id if opportunity else None,
                    "href": "/marketplace/minhas-candidaturas",
                },
                dedupe_key=(
                    f"app_approved:{opportunity.id}:{doctor.id}"
                    if opportunity
                    else None
                ),
                commit=commit,
            )
        return self.create(
            session,
            user_id=doctor.user_id,
            type=TYPE_APPLICATION_REJECTED,
            title="Candidatura não selecionada",
            body=f"Sua candidatura em {hospital_name} não foi selecionada.",
            data={
                "opportunity_id": opportunity.id if opportunity else None,
                "href": "/marketplace/minhas-candidaturas",
            },
            dedupe_key=(
                f"app_rejected:{opportunity.id}:{doctor.id}" if opportunity else None
            ),
            commit=commit,
        )

    def notify_new_application(
        self,
        session: Session,
        *,
        opportunity,
        doctor: Doctor,
        application_id: int,
        commit: bool = True,
    ) -> int:
        hospital_id = opportunity.hospital_id
        specialty = opportunity.specialty
        when = _fmt_date(opportunity.date)
        body = f"Dr(a). {doctor.name} candidatou-se à vaga de {specialty} em {when}."
        return self.notify_hospital_staff(
            session,
            hospital_id=hospital_id,
            type=TYPE_NEW_APPLICATION,
            title="Nova candidatura",
            body=body,
            data={
                "opportunity_id": opportunity.id,
                "application_id": application_id,
                "doctor_id": doctor.id,
                "href": f"/hospital/opportunities/{opportunity.id}",
            },
            dedupe_key_prefix=f"new_app:{application_id}",
            commit=commit,
        )

    def notify_opportunity_filled(
        self, session: Session, *, opportunity, commit: bool = True
    ) -> int:
        return self.notify_hospital_staff(
            session,
            hospital_id=opportunity.hospital_id,
            type=TYPE_OPPORTUNITY_FILLED,
            title="Vaga preenchida",
            body=f"A vaga de {opportunity.specialty} em {_fmt_date(opportunity.date)} foi preenchida.",
            data={
                "opportunity_id": opportunity.id,
                "href": f"/hospital/opportunities/{opportunity.id}",
            },
            dedupe_key_prefix=f"opp_filled:{opportunity.id}",
            commit=commit,
        )

    def run_daily_job(self, session: Session) -> dict[str, int]:
        brazil_tz = pytz.timezone("America/Sao_Paulo")
        today = datetime.now(brazil_tz).date()
        tomorrow = today + timedelta(days=1)

        tomorrow_shifts = (
            session.query(Shift)
            .options(
                joinedload(Shift.doctor),
                joinedload(Shift.hospital),
            )
            .filter(
                Shift.date == tomorrow,
                Shift.status == "scheduled",
            )
            .all()
        )
        shift_count = 0
        for shift in tomorrow_shifts:
            if self.notify_doctor_shift_tomorrow(session, shift, commit=False):
                shift_count += 1

        from app.models.payment import Payment

        pending_shifts = (
            session.query(Shift)
            .options(
                joinedload(Shift.doctor),
                joinedload(Shift.hospital),
                joinedload(Shift.payment),
            )
            .outerjoin(Payment, Payment.shift_id == Shift.id)
            .filter(
                Shift.payment_date.isnot(None),
                Shift.payment_date <= today,
                Shift.status.in_(["scheduled", "completed"]),
                or_(Payment.id.is_(None), Payment.status != "paid"),
            )
            .all()
        )
        payment_count = 0
        for shift in pending_shifts:
            if self.notify_doctor_payment_pending(session, shift, commit=False):
                payment_count += 1

        session.commit()
        return {
            "shift_tomorrow": shift_count,
            "payment_pending": payment_count,
            "date": today.isoformat(),
        }


notification_service = NotificationService()
