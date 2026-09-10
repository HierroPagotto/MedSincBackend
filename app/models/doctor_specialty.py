from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import db


class DoctorSpecialty(db.Model):
    __tablename__ = "doctor_specialties"
    __table_args__ = (
        UniqueConstraint("doctor_id", "specialty", name="uq_doctor_specialty"),
    )

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    specialty = Column(String(100), nullable=False)

    doctor = relationship("Doctor", back_populates="specialty_rows")


class DoctorPracticeArea(db.Model):
    __tablename__ = "doctor_practice_areas"
    __table_args__ = (
        UniqueConstraint("doctor_id", "area", name="uq_doctor_practice_area"),
    )

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    area = Column(String(100), nullable=False)

    doctor = relationship("Doctor", back_populates="practice_area_rows")
