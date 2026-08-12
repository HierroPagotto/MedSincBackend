from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.doctor import DoctorCreate, DoctorUpdate
from app.repositories.user_repository import UserRepository
from app.utils.passwords import hash_password
from app.utils.security import ROLE_DOCTOR


class DoctorRepository:
    model = Doctor

    def __init__(self):
        self.user_repository = UserRepository()

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

        db_doctor = Doctor(
            user_id=user.id,
            name=doctor.name,
            photo_url=doctor.photo_url,
            email=email,
            password=hashed_password,
            crm=doctor.crm,
            crm_state=doctor.crm_state,
            graduation_year=doctor.graduation_year,
            city=doctor.city,
            phone=doctor.phone,
            main_specialty=doctor.main_specialty,
            procedures=doctor.procedures,
            shift_types=doctor.shift_types,
            preferred_periods=doctor.preferred_periods,
            preferred_days=doctor.preferred_days,
            accepts_fixed_shifts=doctor.accepts_fixed_shifts,
            accepts_temporary_shifts=doctor.accepts_temporary_shifts,
            max_distance_km=doctor.max_distance_km,
            state=doctor.state,
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
        db.commit()
        db.refresh(db_doctor)
        return db_doctor

    def update(self, db: Session, doctor: Doctor, update_data: DoctorUpdate) -> Doctor:
        for field, value in update_data.__dict__.items():
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
