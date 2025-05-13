from sqlalchemy.orm import Session
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate
from datetime import datetime

class PaymentRepository:
    model = Payment
    
    def create(self, db: Session, payment: PaymentCreate) -> Payment:
        db_payment = Payment(**vars(payment), status="pending")
        db.add(db_payment)
        db.commit()
        db.refresh(db_payment)
        return db_payment

    def get_by_shift(self, db: Session, shift_id: int) -> Payment:
        return db.query(Payment).filter(Payment.shift_id == shift_id).first()

    def update_status(self, db: Session, payment: Payment, status: str) -> Payment:
        payment.status = status
        if status == "paid":
            payment.payment_date = datetime.utcnow()
        db.commit()
        db.refresh(payment)
        return payment