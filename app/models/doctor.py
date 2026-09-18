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

    profession = Column(String(40), nullable=False, default="doctor", index=True)
    council_type = Column(String(20), nullable=True)
    council_number = Column(String(20), nullable=True)
    council_state = Column(String(2), nullable=True)

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
    specialty_rows = relationship(
        "DoctorSpecialty",
        back_populates="doctor",
        cascade="all, delete-orphan",
        lazy="joined",
    )
    practice_area_rows = relationship(
        "DoctorPracticeArea",
        back_populates="doctor",
        cascade="all, delete-orphan",
        lazy="joined",
    )

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

        specialties = [row.specialty for row in (self.specialty_rows or [])]
        practice_areas = [row.area for row in (self.practice_area_rows or [])]
        if not specialties and self.main_specialty:
            specialties = [self.main_specialty]
        result["specialties"] = specialties
        result["practice_areas"] = practice_areas

        if not result.get("council_number") and result.get("crm"):
            result["council_type"] = result.get("council_type") or "CRM"
            result["council_number"] = result.get("crm")
            result["council_state"] = result.get("council_state") or result.get(
                "crm_state"
            )
        from app.utils.professions import normalize_profession

        result["profession"] = (
            normalize_profession(result.get("profession")) or "doctor"
        )

        if include_shifts and self.shifts:
            result["shifts"] = [shift.to_dict() for shift in self.shifts]

        if include_shifts_count:
            result["shifts_count"] = len(self.shifts) if self.shifts else 0

        return result

    def to_public_dict(self, include_shifts_count=False):
        """Dados mínimos para perfil público (minimização LGPD)."""
        from app.utils.professions import normalize_profession

        specialties = [row.specialty for row in (self.specialty_rows or [])]
        practice_areas = [row.area for row in (self.practice_area_rows or [])]
        if not specialties and self.main_specialty:
            specialties = [self.main_specialty]

        data = {
            "id": self.id,
            "name": self.name,
            "photo_url": self.photo_url,
            "profession": normalize_profession(self.profession) or "doctor",
            "main_specialty": self.main_specialty,
            "specialties": specialties,
            "practice_areas": practice_areas,
            "city": self.city,
            "state": self.state,
            "graduation_year": self.graduation_year,
            "years_of_experience": self.years_of_experience,
            "acls": bool(self.acls),
            "bls": bool(self.bls),
            "atls": bool(self.atls),
            "pals": bool(self.pals),
            "other_certifications": self.other_certifications,
            "procedures": self.procedures,
            "languages": self.languages,
            "provides_invoice": bool(self.provides_invoice),
            "council_type": self.council_type
            or ("CRM" if self.crm else None),
            "council_state": self.council_state or self.crm_state,
            "council_number": self.council_number or self.crm,
            "crm": self.crm,
            "crm_state": self.crm_state,
        }
        if include_shifts_count:
            data["shifts_count"] = len(self.shifts) if self.shifts else 0
        return data
