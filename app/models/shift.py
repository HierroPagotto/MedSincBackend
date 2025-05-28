from sqlalchemy import Column, Integer, String, DateTime, Date, Time, ForeignKey, Numeric, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import db
import datetime
import decimal

class Shift(db.Model):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    week_days = Column(JSON, nullable=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    value = Column(Numeric(10, 2), nullable=False)
    specialty = Column(String(100), nullable=False)
    payment_date = Column(Date, nullable=True)
    status = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    doctor = relationship("Doctor", back_populates="shifts")
    hospital = relationship("Hospital", back_populates="shifts")
    payment = relationship("Payment", back_populates="shift", uselist=False)

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

        if self.hospital:
            result["hospital"] = self.hospital.to_dict()

        return result


