import decimal

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Date,
    ForeignKey,
    Numeric,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import db

KIND_SHIFT = "shift"
KIND_PRIVATE = "private"

ATTENDANCE_KINDS = {
    KIND_SHIFT: "Plantão",
    KIND_PRIVATE: "Consulta particular",
}

VALID_ATTENDANCE_KINDS = frozenset(ATTENDANCE_KINDS.keys())

PAYMENT_STATUS_OPTIONS = {
    "pending": "Pendente",
    "paid": "Pago",
}

VALID_PAYMENT_STATUSES = frozenset(PAYMENT_STATUS_OPTIONS.keys())


class Attendance(db.Model):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id = Column(
        Integer,
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shift_id = Column(
        Integer,
        ForeignKey("shifts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    kind = Column(String(20), nullable=False, default=KIND_SHIFT)
    attendance_number = Column(String(50), nullable=True)
    date = Column(Date, nullable=False)
    value = Column(Numeric(10, 2), nullable=True)
    payment_status = Column(String(20), nullable=True)
    location = Column(String(150), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    doctor = relationship("Doctor")
    patient = relationship("Patient", back_populates="attendances")
    shift = relationship("Shift", back_populates="attendances")

    def to_dict(self, include_patient: bool = True):
        result = {
            "id": self.id,
            "doctor_id": self.doctor_id,
            "patient_id": self.patient_id,
            "shift_id": self.shift_id,
            "kind": self.kind,
            "kind_label": ATTENDANCE_KINDS.get(self.kind, self.kind),
            "attendance_number": self.attendance_number,
            "date": self.date.isoformat() if self.date else None,
            "value": (
                float(self.value)
                if isinstance(self.value, decimal.Decimal)
                else self.value
            ),
            "payment_status": self.payment_status,
            "payment_status_label": PAYMENT_STATUS_OPTIONS.get(
                self.payment_status or "", None
            ),
            "location": self.location,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_patient and self.patient:
            result["patient"] = self.patient.to_dict()
        if self.shift:
            hospital = self.shift.hospital
            result["shift"] = {
                "id": self.shift.id,
                "date": self.shift.date.isoformat() if self.shift.date else None,
                "shift_type": self.shift.shift_type,
                "shift_type_label": self.shift.shift_type_label,
                "hospital_name": hospital.name if hospital else None,
            }
        else:
            result["shift"] = None
        return result
