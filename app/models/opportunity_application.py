from datetime import datetime as dt

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import db

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_WITHDRAWN = "withdrawn"


class OpportunityApplication(db.Model):
    __tablename__ = "opportunity_applications"
    __table_args__ = (
        UniqueConstraint(
            "opportunity_id",
            "doctor_id",
            name="uq_opportunity_doctor_application",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    opportunity_id = Column(
        Integer, ForeignKey("shift_opportunities.id"), nullable=False, index=True
    )
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default=STATUS_PENDING, index=True)
    message = Column(Text, nullable=True)
    reviewed_by_staff_id = Column(
        Integer, ForeignKey("hospital_staff.id"), nullable=True
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    opportunity = relationship("ShiftOpportunity", back_populates="applications")
    doctor = relationship("Doctor")
    reviewed_by = relationship("HospitalStaff", foreign_keys=[reviewed_by_staff_id])

    def to_dict(self, include_doctor=False, include_opportunity=False):
        result = {
            "id": self.id,
            "opportunity_id": self.opportunity_id,
            "doctor_id": self.doctor_id,
            "status": self.status,
            "message": self.message,
            "reviewed_by_staff_id": self.reviewed_by_staff_id,
            "reviewed_at": (
                self.reviewed_at.isoformat()
                if isinstance(self.reviewed_at, dt)
                else self.reviewed_at
            ),
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
        if include_doctor and self.doctor:
            result["doctor"] = {
                "id": self.doctor.id,
                "name": self.doctor.name,
                "profession": getattr(self.doctor, "profession", None) or "doctor",
                "council_type": getattr(self.doctor, "council_type", None),
                "council_number": getattr(self.doctor, "council_number", None)
                or self.doctor.crm,
                "council_state": getattr(self.doctor, "council_state", None)
                or self.doctor.crm_state,
                "crm": self.doctor.crm,
                "crm_state": self.doctor.crm_state,
                "main_specialty": self.doctor.main_specialty,
                "specialties": [
                    row.specialty
                    for row in (getattr(self.doctor, "specialty_rows", None) or [])
                ]
                or ([self.doctor.main_specialty] if self.doctor.main_specialty else []),
                "practice_areas": [
                    row.area
                    for row in (getattr(self.doctor, "practice_area_rows", None) or [])
                ],
                "city": self.doctor.city,
                "state": self.doctor.state,
                "photo_url": self.doctor.photo_url,
                "acls": self.doctor.acls,
                "bls": self.doctor.bls,
                "atls": self.doctor.atls,
                "pals": self.doctor.pals,
                "years_of_experience": self.doctor.years_of_experience,
            }
        if include_opportunity and self.opportunity:
            result["opportunity"] = self.opportunity.to_dict(include_hospital=True)
        return result
