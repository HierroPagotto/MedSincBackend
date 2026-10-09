import datetime

from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import db


def only_digits(raw) -> str:
    return "".join(ch for ch in str(raw or "") if ch.isdigit())


def format_phone(digits: str | None) -> str | None:
    if not digits:
        return None
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    return digits


def format_cpf(digits: str | None) -> str | None:
    if not digits or len(digits) != 11:
        return digits or None
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def cpf_is_valid(digits: str) -> bool:
    if len(digits) != 11 or digits == digits[0] * 11:
        return False

    def check_digit(base: str, factor: int) -> str:
        total = sum(
            int(char) * weight for char, weight in zip(base, range(factor, 1, -1))
        )
        rest = (total * 10) % 11
        return "0" if rest == 10 else str(rest)

    return digits[-2:] == check_digit(digits[:9], 10) + check_digit(digits[:10], 11)


def parse_phone(raw):
    if raw is None or str(raw).strip() == "":
        return None, None
    digits = only_digits(raw)
    if len(digits) not in (10, 11):
        return None, "Informe um telefone com DDD e 8 ou 9 dígitos"
    return digits, None


def parse_cpf(raw):
    if raw is None or str(raw).strip() == "":
        return None, None
    digits = only_digits(raw)
    if not cpf_is_valid(digits):
        return None, "CPF inválido"
    return digits, None


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
    phone = Column(String(20), nullable=True)
    cpf = Column(String(11), nullable=True)
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
            "phone": self.phone,
            "phone_display": format_phone(self.phone),
            "cpf": self.cpf,
            "cpf_display": format_cpf(self.cpf),
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
