from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.shift_expense import (
    ShiftExpense,
    VALID_EXPENSE_CATEGORIES,
)


class ShiftExpenseRepository:
    def list_by_shift(self, db: Session, shift_id: int) -> list[ShiftExpense]:
        return (
            db.query(ShiftExpense)
            .filter(ShiftExpense.shift_id == shift_id)
            .order_by(ShiftExpense.id.asc())
            .all()
        )

    def get_by_id(self, db: Session, expense_id: int) -> ShiftExpense | None:
        return db.query(ShiftExpense).filter(ShiftExpense.id == expense_id).first()

    def create(
        self,
        db: Session,
        *,
        shift_id: int,
        doctor_id: int,
        category: str,
        amount: Decimal,
        description: str | None,
        expense_date,
    ) -> ShiftExpense:
        expense = ShiftExpense(
            shift_id=shift_id,
            doctor_id=doctor_id,
            category=category,
            amount=amount,
            description=description,
            expense_date=expense_date,
        )
        db.add(expense)
        db.commit()
        db.refresh(expense)
        return expense

    def update(
        self,
        db: Session,
        expense: ShiftExpense,
        *,
        category: str | None = None,
        amount: Decimal | None = None,
        description: str | None = None,
        expense_date=None,
    ) -> ShiftExpense:
        if category is not None:
            expense.category = category
        if amount is not None:
            expense.amount = amount
        if description is not None:
            expense.description = description
        if expense_date is not None:
            expense.expense_date = expense_date
        db.commit()
        db.refresh(expense)
        return expense

    def delete(self, db: Session, expense: ShiftExpense) -> None:
        db.delete(expense)
        db.commit()

    def sync_dates_for_shift(self, db: Session, shift_id: int, expense_date) -> None:
        db.query(ShiftExpense).filter(ShiftExpense.shift_id == shift_id).update(
            {"expense_date": expense_date}, synchronize_session=False
        )
        db.commit()


def parse_expense_amount(raw) -> Decimal | None:
    try:
        amount = Decimal(str(raw))
    except Exception:
        return None
    if amount <= 0:
        return None
    return amount.quantize(Decimal("0.01"))


def validate_category(category: str | None) -> str | None:
    if not category or category not in VALID_EXPENSE_CATEGORIES:
        return None
    return category
