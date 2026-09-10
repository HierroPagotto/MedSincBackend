from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.doctor import Doctor
from app.models.doctor_specialty import DoctorSpecialty, DoctorPracticeArea
from app.models.user import User
from app.schemas.doctor import DoctorCreate, DoctorUpdate
from app.repositories.user_repository import UserRepository
from app.utils.passwords import hash_password
from app.utils.security import ROLE_DOCTOR
from app.utils.professions import (
    PROFESSION_DOCTOR,
    default_council_for,
    normalize_profession,
    sync_legacy_crm_fields,
)


class DoctorRepository:
    model = Doctor

    def __init__(self):
        self.user_repository = UserRepository()

    @staticmethod
    def _blank_to_none(value):
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @staticmethod
    def _normalize_list(values) -> list[str]:
        if not values:
            return []
        if isinstance(values, str):
            parts = [p.strip() for p in values.split(",")]
            return [p for p in parts if p]
        result = []
        for item in values:
            text = str(item or "").strip()
            if text and text not in result:
                result.append(text)
        return result

    def _replace_specialties(self, db: Session, doctor: Doctor, specialties: list[str]):
        doctor.specialty_rows.clear()
        db.flush()
        for name in specialties:
            doctor.specialty_rows.append(
                DoctorSpecialty(doctor_id=doctor.id, specialty=name)
            )
        if specialties:
            doctor.main_specialty = specialties[0]

    def _replace_practice_areas(self, db: Session, doctor: Doctor, areas: list[str]):
        doctor.practice_area_rows.clear()
        db.flush()
        for name in areas:
            doctor.practice_area_rows.append(
                DoctorPracticeArea(doctor_id=doctor.id, area=name)
            )

    def create(self, db: Session, doctor: DoctorCreate) -> Doctor:
        hashed_password = hash_password(doctor.password)
        email = doctor.email.strip().lower()

        user = self.user_repository.create(
            db,
            email=email,
            password=hashed_password,
            role=ROLE_DOCTOR,
            commit=False,
            already_hashed=True,
        )

        profession = normalize_profession(doctor.profession) or PROFESSION_DOCTOR
        specialties = self._normalize_list(doctor.specialties)
        if not specialties and doctor.main_specialty:
            specialties = [doctor.main_specialty.strip()]
        main_specialty = (
            specialties[0] if specialties else doctor.main_specialty.strip()
        )

        council_number = self._blank_to_none(
            doctor.council_number
        ) or self._blank_to_none(doctor.crm)
        council_state = self._blank_to_none(
            doctor.council_state
        ) or self._blank_to_none(doctor.crm_state)
        council_type = self._blank_to_none(doctor.council_type) or default_council_for(
            profession
        )
        synced = sync_legacy_crm_fields(
            profession, council_type, council_number, council_state
        )

        db_doctor = Doctor(
            user_id=user.id,
            name=doctor.name,
            photo_url=doctor.photo_url,
            email=email,
            password=hashed_password,
            profession=profession,
            council_type=synced["council_type"],
            council_number=synced["council_number"],
            council_state=synced["council_state"],
            crm=synced["crm"],
            crm_state=synced["crm_state"],
            graduation_year=doctor.graduation_year,
            city=self._blank_to_none(doctor.city),
            phone=self._blank_to_none(doctor.phone),
            main_specialty=main_specialty,
            procedures=doctor.procedures,
            shift_types=doctor.shift_types,
            preferred_periods=doctor.preferred_periods,
            preferred_days=doctor.preferred_days,
            accepts_fixed_shifts=doctor.accepts_fixed_shifts,
            accepts_temporary_shifts=doctor.accepts_temporary_shifts,
            max_distance_km=doctor.max_distance_km,
            state=self._blank_to_none(doctor.state),
            cities_of_work=doctor.cities_of_work,
            acls=doctor.acls,
            bls=doctor.bls,
            atls=doctor.atls,
            pals=doctor.pals,
            other_certifications=doctor.other_certifications,
            main_hospitals=doctor.main_hospitals,
            years_of_experience=doctor.years_of_experience,
            has_driver_license=doctor.has_driver_license,
            has_ehr_experience=doctor.has_ehr_experience,
            provides_invoice=doctor.provides_invoice,
            languages=doctor.languages,
        )
        db.add(db_doctor)
        db.flush()

        for name in specialties:
            db.add(DoctorSpecialty(doctor_id=db_doctor.id, specialty=name))
        for name in self._normalize_list(doctor.practice_areas):
            db.add(DoctorPracticeArea(doctor_id=db_doctor.id, area=name))

        db.commit()
        db.refresh(db_doctor)
        return db_doctor

    def update(self, db: Session, doctor: Doctor, update_data: DoctorUpdate) -> Doctor:
        data = dict(update_data.__dict__)
        specialties = data.pop("specialties", None)
        practice_areas = data.pop("practice_areas", None)

        if data.get("profession") is not None:
            data["profession"] = (
                normalize_profession(data["profession"]) or doctor.profession
            )

        # Se mandou crm legado sem council, espelha
        if data.get("council_number") is None and data.get("crm") is not None:
            data["council_number"] = data["crm"]
        if data.get("council_state") is None and data.get("crm_state") is not None:
            data["council_state"] = data["crm_state"]

        profession = data.get("profession") or doctor.profession
        if any(
            data.get(k) is not None
            for k in (
                "council_type",
                "council_number",
                "council_state",
                "crm",
                "crm_state",
                "profession",
            )
        ):
            synced = sync_legacy_crm_fields(
                profession,
                (
                    data.get("council_type")
                    if data.get("council_type") is not None
                    else doctor.council_type
                ),
                (
                    data.get("council_number")
                    if data.get("council_number") is not None
                    else doctor.council_number
                ),
                (
                    data.get("council_state")
                    if data.get("council_state") is not None
                    else doctor.council_state
                ),
            )
            data.update(synced)

        for field, value in data.items():
            if value is None:
                continue
            if field == "password":
                hashed = hash_password(value)
                setattr(doctor, field, hashed)
                if doctor.user_id:
                    user = db.query(User).filter(User.id == doctor.user_id).first()
                    if user:
                        user.password = hashed
                elif doctor.email:
                    user = db.query(User).filter(User.email == doctor.email).first()
                    if user:
                        user.password = hashed
                        doctor.user_id = user.id
            elif field == "email":
                email = value.strip().lower()
                setattr(doctor, field, email)
                if doctor.user_id:
                    user = db.query(User).filter(User.id == doctor.user_id).first()
                    if user:
                        user.email = email
            else:
                setattr(doctor, field, value)

        if specialties is not None:
            normalized = self._normalize_list(specialties)
            if normalized:
                self._replace_specialties(db, doctor, normalized)
        elif data.get("main_specialty"):
            # Se só veio main_specialty e ainda não há rows, sincroniza
            if not doctor.specialty_rows:
                self._replace_specialties(db, doctor, [data["main_specialty"].strip()])

        if practice_areas is not None:
            self._replace_practice_areas(
                db, doctor, self._normalize_list(practice_areas)
            )

        db.commit()
        db.refresh(doctor)
        return doctor

    def get_by_email(self, db: Session, email: str) -> Doctor:
        return (
            db.query(Doctor)
            .filter(func.lower(Doctor.email) == email.strip().lower())
            .first()
        )

    def get_by_id(self, db: Session, doctor_id: int) -> Doctor:
        return db.query(Doctor).filter(Doctor.id == doctor_id).first()

    def get_by_user_id(self, db: Session, user_id: int) -> Doctor:
        return db.query(Doctor).filter(Doctor.user_id == user_id).first()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100):
        doctors = db.query(Doctor).offset(skip).limit(limit).all()
        count = db.query(Doctor).count()
        return doctors, count
