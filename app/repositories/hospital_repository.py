from sqlalchemy.orm import Session
from app.models.hospital import Hospital
from app.schemas.hospital import HospitalCreate

class HospitalRepository:
    model = Hospital
    
    def create(self, db: Session, hospital: HospitalCreate) -> Hospital:
        db_hospital = Hospital(**vars(hospital))
        db.add(db_hospital)
        db.commit()
        return db_hospital

    def get_all(self, db: Session):
        return db.query(Hospital).all()

    def get_by_id(self, db: Session, hospital_id: int) -> Hospital:
        return db.query(Hospital).filter(Hospital.id == hospital_id).first()