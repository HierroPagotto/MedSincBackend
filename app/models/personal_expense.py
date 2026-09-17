import datetime
import decimal

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Date,
    ForeignKey,
    Numeric,
    Boolean,
)
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

RECURRENCE_OPTIONS = {
    "none": "Nenhuma",
    "monthly": "Mensal",
    "bimonthly": "Bimestral",
    "quarterly": "Trimestral",
    "semiannual": "Semestral",
    "annual": "Anual",
}

VALID_RECURRENCES = frozenset(RECURRENCE_OPTIONS.keys())

RECURRENCE_MONTH_STEPS = {
    "monthly": 1,
    "bimonthly": 2,
    "quarterly": 3,
    "semiannual": 6,
    "annual": 12,
}


class PersonalExpense(db.Model):
    __tablename__ = "personal_expenses"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category = Column(String(40), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    description = Column(String(255), nullable=True)
    expense_date = Column(Date, nullable=False)
    recurrence = Column(String(20), nullable=False, default="none")
    payment_method_id = Column(
        Integer,
        ForeignKey("expense_payment_methods.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    recurrence_group_id = Column(String(36), nullable=True, index=True)
    is_recurrence_origin = Column(Boolean, nullable=False, default=False)
    recurrence_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    doctor = relationship("Doctor")
    payment_method = relationship("ExpensePaymentMethod", back_populates="expenses")

    def to_dict(self):
        result = {}
        for c in self.__table__.columns:
            value = getattr(self, c.name)
            if isinstance(value, (datetime.date, datetime.time, datetime.datetime)):
                result[c.name] = value.isoformat()
            elif isinstance(value, decimal.Decimal):
                result[c.name] = float(value)
            elif isinstance(value, bool):
                result[c.name] = bool(value)
            else:
                result[c.name] = value
        result["category_label"] = PERSONAL_EXPENSE_CATEGORIES.get(
            self.category, self.category
        )
        result["recurrence_label"] = RECURRENCE_OPTIONS.get(
            self.recurrence or "none", self.recurrence
        )
        result["payment_method_name"] = (
            self.payment_method.name if self.payment_method else None
        )
        result["source"] = "personal"
        result["shift_id"] = None
        return result
