from datetime import datetime as dt, date, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    DateTime,
    Date,
    Time,
    ForeignKey,
    Numeric,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import db

STATUS_OPEN = "open"
STATUS_FILLED = "filled"
STATUS_CANCELLED = "cancelled"


class ShiftOpportunity(db.Model):
    __tablename__ = "shift_opportunities"

    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(
        Integer, ForeignKey("hospitals.id"), nullable=False, index=True
    )
    created_by_staff_id = Column(
        Integer, ForeignKey("hospital_staff.id"), nullable=False
    )
    date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    specialty = Column(String(100), nullable=False, index=True)
    required_profession = Column(
        String(40),
        nullable=False,
        default="doctor",
        index=True,
        server_default="doctor",
    )
    value = Column(Numeric(10, 2), nullable=False)
    payment_date = Column(Date, nullable=True)
    requires_acls = Column(Boolean, nullable=False, default=False, server_default="0")
    requires_bls = Column(Boolean, nullable=False, default=False, server_default="0")
    requires_atls = Column(Boolean, nullable=False, default=False, server_default="0")
    requires_pals = Column(Boolean, nullable=False, default=False, server_default="0")
    city = Column(String(100), nullable=True, index=True)
    slots_total = Column(Integer, nullable=False, default=1)
    slots_filled = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default=STATUS_OPEN, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    hospital = relationship("Hospital", back_populates="opportunities")
    created_by = relationship("HospitalStaff", foreign_keys=[created_by_staff_id])
    applications = relationship(
        "OpportunityApplication",
        back_populates="opportunity",
        cascade="all, delete-orphan",
    )
    shifts = relationship("Shift", back_populates="opportunity")

    @property
    def slots_remaining(self) -> int:
        return max(0, int(self.slots_total or 0) - int(self.slots_filled or 0))

    def to_dict(self, include_hospital=True, include_applications_count=False):
        result = {
            "id": self.id,
            "hospital_id": self.hospital_id,
            "created_by_staff_id": self.created_by_staff_id,
            "date": self.date.isoformat() if isinstance(self.date, date) else self.date,
            "start_time": (
                self.start_time.isoformat()
                if isinstance(self.start_time, time)
                else self.start_time
            ),
            "end_time": (
                self.end_time.isoformat()
                if isinstance(self.end_time, time)
                else self.end_time
            ),
            "specialty": self.specialty,
            "required_profession": self.required_profession or "doctor",
            "value": (
                float(self.value) if isinstance(self.value, Decimal) else self.value
            ),
            "payment_date": (
                self.payment_date.isoformat()
                if isinstance(self.payment_date, date)
                else self.payment_date
            ),
            "requires_acls": bool(self.requires_acls),
            "requires_bls": bool(self.requires_bls),
            "requires_atls": bool(self.requires_atls),
            "requires_pals": bool(self.requires_pals),
            "city": self.city,
            "slots_total": self.slots_total,
            "slots_filled": self.slots_filled,
            "slots_remaining": self.slots_remaining,
            "status": self.status,
            "notes": self.notes,
            "created_at": (
                self.created_at.isoformat()
                if isinstance(self.created_at, dt)
                else self.created_at
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if isinstance(self.updated_at, dt)
                else self.updated_at
            ),
        }
        if include_hospital and self.hospital:
            result["hospital"] = self.hospital.to_dict()
        if include_applications_count:
            result["applications_count"] = (
                len(self.applications) if self.applications else 0
            )
            result["pending_applications_count"] = (
                sum(1 for a in self.applications if a.status == "pending")
                if self.applications
                else 0
            )
        return result
