import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import db

SYSTEM_PAYMENT_METHODS = [
    ("boleto", "Boleto"),
    ("credit_card", "Cartão de crédito"),
    ("debit_card", "Cartão de débito"),
    ("pix", "Pix"),
    ("cash", "Dinheiro"),
    ("transfer", "Transferência"),
    ("other", "Outro"),
]


class ExpensePaymentMethod(db.Model):
    __tablename__ = "expense_payment_methods"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(
        Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name = Column(String(80), nullable=False)
    slug = Column(String(80), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    doctor = relationship("Doctor")
    expenses = relationship("PersonalExpense", back_populates="payment_method")

    def to_dict(self):
        return {
            "id": self.id,
            "doctor_id": self.doctor_id,
            "name": self.name,
            "slug": self.slug,
            "is_active": bool(self.is_active),
            "is_system": self.doctor_id is None,
            "created_at": (
                self.created_at.isoformat()
                if isinstance(self.created_at, datetime.datetime)
                else self.created_at
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if isinstance(self.updated_at, datetime.datetime)
                else self.updated_at
            ),
        }
