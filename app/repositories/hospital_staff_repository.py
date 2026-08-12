from sqlalchemy.orm import Session

from app.models.hospital_staff import HospitalStaff


class HospitalStaffRepository:
    model = HospitalStaff

    def get_by_id(self, db: Session, staff_id: int) -> HospitalStaff | None:
        return db.query(HospitalStaff).filter(HospitalStaff.id == staff_id).first()

    def get_by_user_id(self, db: Session, user_id: int) -> HospitalStaff | None:
        return db.query(HospitalStaff).filter(HospitalStaff.user_id == user_id).first()

    def list_by_hospital(self, db: Session, hospital_id: int) -> list[HospitalStaff]:
        return (
            db.query(HospitalStaff)
            .filter(HospitalStaff.hospital_id == hospital_id)
            .order_by(HospitalStaff.id.asc())
            .all()
        )

    def create(
        self,
        db: Session,
        *,
        user_id: int,
        hospital_id: int,
        staff_role: str,
        name: str,
        phone: str | None = None,
        commit: bool = True,
    ) -> HospitalStaff:
        staff = HospitalStaff(
            user_id=user_id,
            hospital_id=hospital_id,
            staff_role=staff_role,
            name=name,
            phone=phone,
        )
        db.add(staff)
        if commit:
            db.commit()
            db.refresh(staff)
        else:
            db.flush()
        return staff
