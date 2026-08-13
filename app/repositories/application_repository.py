from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.models.opportunity_application import (
    OpportunityApplication,
    STATUS_PENDING,
    STATUS_REJECTED,
    STATUS_WITHDRAWN,
)
from app.models.shift_opportunity import ShiftOpportunity


class ApplicationRepository:
    model = OpportunityApplication

    def create(
        self,
        db: Session,
        *,
        opportunity_id: int,
        doctor_id: int,
        message: str | None = None,
        commit: bool = True,
    ) -> OpportunityApplication:
        application = OpportunityApplication(
            opportunity_id=opportunity_id,
            doctor_id=doctor_id,
            status=STATUS_PENDING,
            message=message,
        )
        db.add(application)
        if commit:
            db.commit()
            db.refresh(application)
        else:
            db.flush()
        return application

    def get_by_id(
        self, db: Session, application_id: int
    ) -> OpportunityApplication | None:
        return (
            db.query(OpportunityApplication)
            .options(
                joinedload(OpportunityApplication.doctor),
                joinedload(OpportunityApplication.opportunity).joinedload(
                    ShiftOpportunity.hospital
                ),
            )
            .filter(OpportunityApplication.id == application_id)
            .first()
        )

    def get_by_opportunity_and_doctor(
        self, db: Session, opportunity_id: int, doctor_id: int
    ) -> OpportunityApplication | None:
        return (
            db.query(OpportunityApplication)
            .filter(
                OpportunityApplication.opportunity_id == opportunity_id,
                OpportunityApplication.doctor_id == doctor_id,
            )
            .first()
        )

    def list_by_opportunity(self, db: Session, opportunity_id: int):
        return (
            db.query(OpportunityApplication)
            .options(joinedload(OpportunityApplication.doctor))
            .filter(OpportunityApplication.opportunity_id == opportunity_id)
            .order_by(OpportunityApplication.created_at.asc())
            .all()
        )

    def list_by_doctor(self, db: Session, doctor_id: int):
        return (
            db.query(OpportunityApplication)
            .options(
                joinedload(OpportunityApplication.opportunity).joinedload(
                    ShiftOpportunity.hospital
                )
            )
            .filter(OpportunityApplication.doctor_id == doctor_id)
            .order_by(OpportunityApplication.created_at.desc())
            .all()
        )

    def withdraw(
        self, db: Session, application: OpportunityApplication
    ) -> OpportunityApplication:
        application.status = STATUS_WITHDRAWN
        db.commit()
        db.refresh(application)
        return application

    def mark_reviewed(
        self,
        db: Session,
        application: OpportunityApplication,
        *,
        status: str,
        staff_id: int,
        commit: bool = True,
    ) -> OpportunityApplication:
        application.status = status
        application.reviewed_by_staff_id = staff_id
        application.reviewed_at = datetime.now(timezone.utc)
        if commit:
            db.commit()
            db.refresh(application)
        return application

    def reject_pending_for_opportunity(
        self,
        db: Session,
        opportunity_id: int,
        *,
        except_application_id: int,
        staff_id: int,
        commit: bool = False,
    ) -> int:
        pending = (
            db.query(OpportunityApplication)
            .filter(
                OpportunityApplication.opportunity_id == opportunity_id,
                OpportunityApplication.status == STATUS_PENDING,
                OpportunityApplication.id != except_application_id,
            )
            .all()
        )
        now = datetime.now(timezone.utc)
        for app in pending:
            app.status = STATUS_REJECTED
            app.reviewed_by_staff_id = staff_id
            app.reviewed_at = now
        if commit:
            db.commit()
        return len(pending)
