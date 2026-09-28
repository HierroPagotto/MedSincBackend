import datetime

from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import db


def calculate_age(
    birth_date: datetime.date | None, reference: datetime.date | None = None
):
    if not birth_date:
        return None
    ref = reference or datetime.date.today()
    age = ref.year - birth_date.year
    if (ref.month, ref.day) < (birth_date.month, birth_date.day):
        age -= 1
    return max(age, 0)


class Patient(db.Model):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(150), nullable=False)
    birth_date = Column(Date, nullable=True)
    health_plan = Column(String(100), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    doctor = relationship("Doctor")
    attendances = relationship(
        "Attendance",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def to_dict(self, include_attendances: bool = False):
        result = {
            "id": self.id,
            "doctor_id": self.doctor_id,
            "name": self.name,
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "age": calculate_age(self.birth_date),
            "health_plan": self.health_plan,
            "is_private": not (self.health_plan or "").strip(),
            "active": bool(self.active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_attendances:
            from app.models.attendance import Attendance

            rows = self.attendances.order_by(
                Attendance.date.desc(), Attendance.id.desc()
            ).all()
            result["attendances"] = [a.to_dict(include_patient=False) for a in rows]
            result["attendances_count"] = len(rows)
        return result
