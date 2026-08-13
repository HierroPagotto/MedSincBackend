from datetime import date, datetime, time

from sqlalchemy.orm import Session, joinedload

from app.models.shift_opportunity import (
    ShiftOpportunity,
    STATUS_OPEN,
    STATUS_CANCELLED,
)
from app.schemas.marketplace import OpportunityCreate, OpportunityUpdate


class OpportunityRepository:
    model = ShiftOpportunity

    def create(
        self,
        db: Session,
        *,
        hospital_id: int,
        created_by_staff_id: int,
        data: OpportunityCreate,
        commit: bool = True,
    ) -> ShiftOpportunity:
        opportunity = ShiftOpportunity(
            hospital_id=hospital_id,
            created_by_staff_id=created_by_staff_id,
            date=data.date,
            start_time=data.start_time,
            end_time=data.end_time,
            specialty=data.specialty,
            value=data.value,
            city=data.city,
            slots_total=max(1, int(data.slots_total or 1)),
            slots_filled=0,
            status=STATUS_OPEN,
            notes=data.notes,
        )
        db.add(opportunity)
        if commit:
            db.commit()
            db.refresh(opportunity)
        else:
            db.flush()
        return opportunity

    def get_by_id(self, db: Session, opportunity_id: int) -> ShiftOpportunity | None:
        return (
            db.query(ShiftOpportunity)
            .options(
                joinedload(ShiftOpportunity.hospital),
                joinedload(ShiftOpportunity.applications),
            )
            .filter(ShiftOpportunity.id == opportunity_id)
            .first()
        )

    def list_open(
        self,
        db: Session,
        *,
        city: str | None = None,
        specialty: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[ShiftOpportunity]:
        query = (
            db.query(ShiftOpportunity)
            .options(joinedload(ShiftOpportunity.hospital))
            .filter(ShiftOpportunity.status == STATUS_OPEN)
            .filter(ShiftOpportunity.slots_filled < ShiftOpportunity.slots_total)
        )
        if city:
            query = query.filter(ShiftOpportunity.city.ilike(f"%{city}%"))
        if specialty:
            query = query.filter(ShiftOpportunity.specialty.ilike(f"%{specialty}%"))
        if date_from:
            query = query.filter(ShiftOpportunity.date >= date_from)
        if date_to:
            query = query.filter(ShiftOpportunity.date <= date_to)
        return query.order_by(
            ShiftOpportunity.date.asc(), ShiftOpportunity.start_time.asc()
        ).all()

    def list_by_hospital(
        self, db: Session, hospital_id: int, status: str | None = None
    ):
        query = (
            db.query(ShiftOpportunity)
            .options(
                joinedload(ShiftOpportunity.hospital),
                joinedload(ShiftOpportunity.applications),
            )
            .filter(ShiftOpportunity.hospital_id == hospital_id)
        )
        if status:
            query = query.filter(ShiftOpportunity.status == status)
        return query.order_by(
            ShiftOpportunity.date.desc(), ShiftOpportunity.id.desc()
        ).all()

    def update(
        self, db: Session, opportunity: ShiftOpportunity, data: OpportunityUpdate
    ) -> ShiftOpportunity:
        for field, value in data.__dict__.items():
            if value is not None:
                if field == "slots_total":
                    value = max(int(opportunity.slots_filled or 0), int(value))
                setattr(opportunity, field, value)
        db.commit()
        db.refresh(opportunity)
        return opportunity

    def cancel(self, db: Session, opportunity: ShiftOpportunity) -> ShiftOpportunity:
        opportunity.status = STATUS_CANCELLED
        db.commit()
        db.refresh(opportunity)
        return opportunity
