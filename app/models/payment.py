from datetime import datetime
import decimal
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import db

class Payment(db.Model):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False)
    payment_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    shift = relationship("Shift", back_populates="payment")
    
    def to_dict(self):
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            elif isinstance(value, decimal.Decimal):
                result[column.name] = float(value)
            else:
                result[column.name] = value
                
        if self.shift:
            result["shift"] = self.shift.to_dict()
            
        return result