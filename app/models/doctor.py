from datetime import datetime as dt
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import db


class Doctor(db.Model):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), unique=True, nullable=True, index=True
    )

    name = Column(String(100), nullable=False)
    photo_url = Column(String(255))
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    crm = Column(String(20), unique=True, nullable=True)
    crm_state = Column(String(2), nullable=True)
    graduation_year = Column(Integer, nullable=True)
    city = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)

    main_specialty = Column(String(100), nullable=False)
    procedures = Column(Text)
    shift_types = Column(Text)

    preferred_periods = Column(Text)
    preferred_days = Column(Text)
    accepts_fixed_shifts = Column(Boolean, default=True)
    accepts_temporary_shifts = Column(Boolean, default=True)
    max_distance_km = Column(Integer)

    state = Column(String(2), nullable=True)
    cities_of_work = Column(Text)

    acls = Column(Boolean, default=False)
    bls = Column(Boolean, default=False)
    atls = Column(Boolean, default=False)
    pals = Column(Boolean, default=False)
    other_certifications = Column(String(255))

    main_hospitals = Column(String(500))
    years_of_experience = Column(String(10))

    has_driver_license = Column(Boolean, default=False)
    has_ehr_experience = Column(Boolean, default=False)
    provides_invoice = Column(Boolean, default=False)
    languages = Column(String(255))

    is_admin = Column(Boolean, default=False)
    lost_pass_code = Column(String(6), nullable=True)
    lost_pass_code_requested_time = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    shifts = relationship("Shift", back_populates="doctor")
    user = relationship("User", back_populates="doctor")

    def to_dict(self, include_shifts=False, include_shifts_count=False):
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)

            if isinstance(value, dt):
                result[column.name] = value.isoformat()
            elif isinstance(value, str) or value is None:
                result[column.name] = value
            elif isinstance(value, bool):
                result[column.name] = value
            else:
                result[column.name] = str(value) if value is not None else None

        result.pop("password", None)

        if include_shifts and self.shifts:
            result["shifts"] = [shift.to_dict() for shift in self.shifts]

        if include_shifts_count:
            result["shifts_count"] = len(self.shifts) if self.shifts else 0

        return result
