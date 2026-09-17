from datetime import date
from decimal import Decimal

from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.models.personal_expense import (
    PersonalExpense,
    VALID_PERSONAL_EXPENSE_CATEGORIES,
)
from app.models.shift_expense import ShiftExpense, EXPENSE_CATEGORIES
from app.repositories.expense_repository import parse_expense_amount


class PersonalExpenseRepository:
    def list_by_doctor(
        self,
        db: Session,
        doctor_id: int,
        *,
        year: int | None = None,
        month: int | None = None,
    ) -> list[PersonalExpense]:
        query = db.query(PersonalExpense).filter(PersonalExpense.doctor_id == doctor_id)
        if year is not None:
            query = query.filter(extract("year", PersonalExpense.expense_date) == year)
        if month is not None:
            query = query.filter(extract("month", PersonalExpense.expense_date) == month)
        return query.order_by(
            PersonalExpense.expense_date.desc(), PersonalExpense.id.desc()
        ).all()

    def get_by_id(self, db: Session, expense_id: int) -> PersonalExpense | None:
        return db.query(PersonalExpense).filter(PersonalExpense.id == expense_id).first()

    def create(
        self,
        db: Session,
        *,
        doctor_id: int,
        category: str,
        amount: Decimal,
        description: str | None,
        expense_date: date,
    ) -> PersonalExpense:
        expense = PersonalExpense(
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
        expense: PersonalExpense,
        *,
        category: str | None = None,
        amount: Decimal | None = None,
        description: str | None = None,
        expense_date: date | None = None,
    ) -> PersonalExpense:
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

    def delete(self, db: Session, expense: PersonalExpense) -> None:
        db.delete(expense)
        db.commit()


def validate_personal_category(category: str | None) -> str | None:
    if not category or category not in VALID_PERSONAL_EXPENSE_CATEGORIES:
        return None
    return category


def list_unified_expenses(
    db: Session,
    doctor_id: int,
    *,
    year: int | None = None,
    month: int | None = None,
    source: str | None = None,
) -> list[dict]:
    items: list[dict] = []

    if source in (None, "personal"):
        personal_repo = PersonalExpenseRepository()
        for expense in personal_repo.list_by_doctor(
            db, doctor_id, year=year, month=month
        ):
            items.append(expense.to_dict())

    if source in (None, "shift"):
        query = db.query(ShiftExpense).filter(ShiftExpense.doctor_id == doctor_id)
        if year is not None:
            query = query.filter(extract("year", ShiftExpense.expense_date) == year)
        if month is not None:
            query = query.filter(extract("month", ShiftExpense.expense_date) == month)
        for expense in query.order_by(
            ShiftExpense.expense_date.desc(), ShiftExpense.id.desc()
        ).all():
            data = expense.to_dict()
            data["source"] = "shift"
            data["category_label"] = EXPENSE_CATEGORIES.get(
                expense.category, expense.category
            )
            items.append(data)

    items.sort(
        key=lambda e: (e.get("expense_date") or "", e.get("id") or 0),
        reverse=True,
    )
    return items


__all__ = [
    "PersonalExpenseRepository",
    "parse_expense_amount",
    "validate_personal_category",
    "list_unified_expenses",
]
