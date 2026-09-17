import datetime
import decimal

from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import db

EXPENSE_CATEGORIES = {
    "fuel": "Combustível",
    "food": "Alimentação",
    "toll": "Pedágio",
    "parking": "Estacionamento",
    "transport": "Transporte",
    "other": "Outro",
}

VALID_EXPENSE_CATEGORIES = frozenset(EXPENSE_CATEGORIES.keys())


class ShiftExpense(db.Model):
    __tablename__ = "shift_expenses"

    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(
        Integer, ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    doctor_id = Column(
        Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category = Column(String(40), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    description = Column(String(255), nullable=True)
    expense_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    shift = relationship("Shift", back_populates="expenses")
    doctor = relationship("Doctor")

    def to_dict(self):
        result = {}
        for c in self.__table__.columns:
            value = getattr(self, c.name)
            if isinstance(value, (datetime.date, datetime.time, datetime.datetime)):
                result[c.name] = value.isoformat()
            elif isinstance(value, decimal.Decimal):
                result[c.name] = float(value)
            else:
                result[c.name] = value
        result["category_label"] = EXPENSE_CATEGORIES.get(self.category, self.category)
        return result
