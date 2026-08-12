from datetime import datetime as dt
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import db


class HospitalStaff(db.Model):
    __tablename__ = "hospital_staff"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    hospital_id = Column(
        Integer, ForeignKey("hospitals.id"), nullable=False, index=True
    )
    staff_role = Column(String(30), nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="hospital_staff")
    hospital = relationship("Hospital", back_populates="staff")

    def to_dict(self, include_hospital=False, include_user=False):
        result = {
            "id": self.id,
            "user_id": self.user_id,
            "hospital_id": self.hospital_id,
            "staff_role": self.staff_role,
            "name": self.name,
            "phone": self.phone,
            "created_at": (
                self.created_at.isoformat()
                if isinstance(self.created_at, dt)
                else self.created_at
            ),
        }
        if include_user and self.user:
            result["email"] = self.user.email
            result["is_active"] = self.user.is_active
        if include_hospital and self.hospital:
            result["hospital"] = self.hospital.to_dict()
        return result
