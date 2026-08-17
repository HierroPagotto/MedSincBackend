from datetime import date, datetime, time

from sqlalchemy.orm import Session, joinedload

from app.models.shift import Shift, SOURCE_MARKETPLACE
from app.models.shift_opportunity import STATUS_OPEN, STATUS_FILLED
from app.models.opportunity_application import (
    OpportunityApplication,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
)
from app.models.hospital_staff import HospitalStaff
from app.repositories.application_repository import ApplicationRepository
from app.repositories.opportunity_repository import OpportunityRepository
from app.utils.schedule import doctor_has_conflicting_shift
from app.utils.marketplace_notifications import notify_doctor_application_result
from app.services.notification_service import notification_service


class MarketplaceService:
    def __init__(self):
        self.opportunities = OpportunityRepository()
        self.applications = ApplicationRepository()

    def approve_application(
        self,
        session: Session,
        *,
        application_id: int,
        staff: HospitalStaff,
    ) -> tuple[dict | None, tuple[dict, int] | None]:
        application = self.applications.get_by_id(session, application_id)
        if not application:
            return None, ({"message": "Candidatura não encontrada"}, 404)

        opportunity = application.opportunity or self.opportunities.get_by_id(
            session, application.opportunity_id
        )
        if not opportunity or opportunity.hospital_id != staff.hospital_id:
            return None, ({"message": "Candidatura não pertence ao seu hospital"}, 403)

        if application.status != STATUS_PENDING:
            return None, (
                {"message": f"Candidatura não está pendente ({application.status})"},
                400,
            )

        if opportunity.status != STATUS_OPEN:
            return None, (
                {"message": f"Oportunidade não está aberta ({opportunity.status})"},
                400,
            )

        if opportunity.slots_remaining <= 0:
            return None, ({"message": "Não há vagas restantes nesta oportunidade"}, 400)

        conflict = doctor_has_conflicting_shift(
            session,
            doctor_id=application.doctor_id,
            opportunity_date=opportunity.date,
            start_time=opportunity.start_time,
            end_time=opportunity.end_time,
        )
        if conflict:
            return None, (
                {
                    "message": "Médico possui plantão conflitante no mesmo horário",
                    "conflicting_shift_id": conflict.id,
                },
                409,
            )

        self.applications.mark_reviewed(
            session,
            application,
            status=STATUS_APPROVED,
            staff_id=staff.id,
            commit=False,
        )

        shift = Shift(
            doctor_id=application.doctor_id,
            hospital_id=opportunity.hospital_id,
            date=opportunity.date,
            start_time=opportunity.start_time,
            end_time=opportunity.end_time,
            value=opportunity.value,
            specialty=opportunity.specialty,
            payment_date=None,
            status="scheduled",
            source=SOURCE_MARKETPLACE,
            opportunity_id=opportunity.id,
        )
        session.add(shift)

        opportunity.slots_filled = int(opportunity.slots_filled or 0) + 1
        rejected_apps: list[OpportunityApplication] = []
        if opportunity.slots_filled >= opportunity.slots_total:
            opportunity.status = STATUS_FILLED
            rejected_apps = (
                session.query(OpportunityApplication)
                .options(joinedload(OpportunityApplication.doctor))
                .filter(
                    OpportunityApplication.opportunity_id == opportunity.id,
                    OpportunityApplication.status == STATUS_PENDING,
                    OpportunityApplication.id != application.id,
                )
                .all()
            )
            self.applications.reject_pending_for_opportunity(
                session,
                opportunity.id,
                except_application_id=application.id,
                staff_id=staff.id,
                commit=False,
            )

        session.commit()
        session.refresh(shift)
        session.refresh(application)
        session.refresh(opportunity)

        if application.doctor:
            notify_doctor_application_result(
                doctor=application.doctor,
                opportunity=opportunity,
                approved=True,
            )
            try:
                notification_service.notify_application_result(
                    session,
                    doctor=application.doctor,
                    opportunity=opportunity,
                    approved=True,
                    commit=False,
                )
            except Exception as exc:
                print(f"Falha notificação in-app aprovação: {exc}")
        for rejected in rejected_apps:
            session.refresh(rejected)
            if rejected.doctor:
                notify_doctor_application_result(
                    doctor=rejected.doctor,
                    opportunity=opportunity,
                    approved=False,
                )
                try:
                    notification_service.notify_application_result(
                        session,
                        doctor=rejected.doctor,
                        opportunity=opportunity,
                        approved=False,
                        commit=False,
                    )
                except Exception as exc:
                    print(f"Falha notificação in-app rejeição: {exc}")

        if opportunity.status == STATUS_FILLED:
            try:
                notification_service.notify_opportunity_filled(
                    session, opportunity=opportunity, commit=False
                )
            except Exception as exc:
                print(f"Falha notificação vaga preenchida: {exc}")

        session.commit()

        return {
            "message": "Candidatura aprovada",
            "application": application.to_dict(include_doctor=True),
            "shift": shift.to_dict(),
            "opportunity": opportunity.to_dict(include_hospital=True),
            "rejected_pending_count": len(rejected_apps),
        }, None

    def reject_application(
        self,
        session: Session,
        *,
        application_id: int,
        staff: HospitalStaff,
    ) -> tuple[dict | None, tuple[dict, int] | None]:
        application = self.applications.get_by_id(session, application_id)
        if not application:
            return None, ({"message": "Candidatura não encontrada"}, 404)

        opportunity = application.opportunity or self.opportunities.get_by_id(
            session, application.opportunity_id
        )
        if not opportunity or opportunity.hospital_id != staff.hospital_id:
            return None, ({"message": "Candidatura não pertence ao seu hospital"}, 403)

        if application.status != STATUS_PENDING:
            return None, (
                {"message": f"Candidatura não está pendente ({application.status})"},
                400,
            )

        self.applications.mark_reviewed(
            session,
            application,
            status=STATUS_REJECTED,
            staff_id=staff.id,
            commit=True,
        )

        if application.doctor and opportunity:
            notify_doctor_application_result(
                doctor=application.doctor,
                opportunity=opportunity,
                approved=False,
            )
            try:
                notification_service.notify_application_result(
                    session,
                    doctor=application.doctor,
                    opportunity=opportunity,
                    approved=False,
                )
            except Exception as exc:
                print(f"Falha notificação in-app rejeição: {exc}")

        return {
            "message": "Candidatura rejeitada",
            "application": application.to_dict(include_doctor=True),
        }, None


def parse_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def parse_time(value) -> time | None:
    if value is None or value == "":
        return None
    if isinstance(value, time) and not isinstance(value, datetime):
        return value
    text = str(value)
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Horário inválido: {value}")
