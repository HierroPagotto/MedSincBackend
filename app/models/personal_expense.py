import datetime
import decimal

from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import db

PERSONAL_EXPENSE_CATEGORIES = {
    "streaming": "Streaming",
    "food": "Alimentação",
    "housing": "Moradia",
    "utilities": "Contas",
    "transport": "Transporte",
    "health": "Saúde",
    "education": "Educação",
    "leisure": "Lazer",
    "shopping": "Compras",
    "other": "Outro",
}

VALID_PERSONAL_EXPENSE_CATEGORIES = frozenset(PERSONAL_EXPENSE_CATEGORIES.keys())


class PersonalExpense(db.Model):
    __tablename__ = "personal_expenses"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(
        Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category = Column(String(40), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    description = Column(String(255), nullable=True)
    expense_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

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
        result["category_label"] = PERSONAL_EXPENSE_CATEGORIES.get(
            self.category, self.category
        )
        result["source"] = "personal"
        result["shift_id"] = None
        return result
