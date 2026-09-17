from __future__ import annotations

import re
import uuid
from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy import extract, or_
from sqlalchemy.orm import Session, joinedload

from app.models.expense_payment_method import ExpensePaymentMethod
from app.models.personal_expense import (
    PERSONAL_EXPENSE_CATEGORIES,
    RECURRENCE_MONTH_STEPS,
    VALID_PERSONAL_EXPENSE_CATEGORIES,
    VALID_RECURRENCES,
    PersonalExpense,
)
from app.models.shift_expense import ShiftExpense, EXPENSE_CATEGORIES
from app.repositories.expense_repository import parse_expense_amount


def add_months(base: date, months: int) -> date:
    year = base.year + (base.month - 1 + months) // 12
    month = (base.month - 1 + months) % 12 + 1
    day = min(base.day, monthrange(year, month)[1])
    return date(year, month, day)


def validate_personal_category(category: str | None) -> str | None:
    if not category or category not in VALID_PERSONAL_EXPENSE_CATEGORIES:
        return None
    return category


def validate_recurrence(recurrence: str | None) -> str | None:
    if recurrence is None:
        return "none"
    if recurrence not in VALID_RECURRENCES:
        return None
    return recurrence


def slugify_payment_method(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower().strip())
    return slug.strip("-")[:80] or "custom"


class PaymentMethodRepository:
    def list_for_doctor(self, db: Session, doctor_id: int) -> list[ExpensePaymentMethod]:
        return (
            db.query(ExpensePaymentMethod)
            .filter(
                ExpensePaymentMethod.is_active.is_(True),
                or_(
                    ExpensePaymentMethod.doctor_id.is_(None),
                    ExpensePaymentMethod.doctor_id == doctor_id,
                ),
            )
            .order_by(
                ExpensePaymentMethod.doctor_id.isnot(None),
                ExpensePaymentMethod.name.asc(),
            )
            .all()
        )

    def get_by_id(self, db: Session, method_id: int) -> ExpensePaymentMethod | None:
        return (
            db.query(ExpensePaymentMethod)
            .filter(ExpensePaymentMethod.id == method_id)
            .first()
        )

    def get_usable(
        self, db: Session, method_id: int, doctor_id: int
    ) -> ExpensePaymentMethod | None:
        method = self.get_by_id(db, method_id)
        if not method or not method.is_active:
            return None
        if method.doctor_id is not None and method.doctor_id != doctor_id:
            return None
        return method

    def create_custom(
        self, db: Session, *, doctor_id: int, name: str
    ) -> ExpensePaymentMethod:
        clean = name.strip()[:80]
        slug = slugify_payment_method(clean)
        existing = (
            db.query(ExpensePaymentMethod)
            .filter(
                ExpensePaymentMethod.doctor_id == doctor_id,
                ExpensePaymentMethod.slug == slug,
            )
            .first()
        )
        if existing:
            existing.is_active = True
            existing.name = clean
            db.commit()
            db.refresh(existing)
            return existing

        method = ExpensePaymentMethod(
            doctor_id=doctor_id,
            name=clean,
            slug=slug,
            is_active=True,
        )
        db.add(method)
        db.commit()
        db.refresh(method)
        return method

    def delete_custom(
        self, db: Session, method: ExpensePaymentMethod
    ) -> None:
        method.is_active = False
        db.commit()


class PersonalExpenseRepository:
    def list_by_doctor(
        self,
        db: Session,
        doctor_id: int,
        *,
        year: int | None = None,
        month: int | None = None,
    ) -> list[PersonalExpense]:
        query = (
            db.query(PersonalExpense)
            .options(joinedload(PersonalExpense.payment_method))
            .filter(PersonalExpense.doctor_id == doctor_id)
        )
        if year is not None:
            query = query.filter(extract("year", PersonalExpense.expense_date) == year)
        if month is not None:
            query = query.filter(extract("month", PersonalExpense.expense_date) == month)
        return query.order_by(
            PersonalExpense.expense_date.desc(), PersonalExpense.id.desc()
        ).all()

    def get_by_id(self, db: Session, expense_id: int) -> PersonalExpense | None:
        return (
            db.query(PersonalExpense)
            .options(joinedload(PersonalExpense.payment_method))
            .filter(PersonalExpense.id == expense_id)
            .first()
        )

    def create(
        self,
        db: Session,
        *,
        doctor_id: int,
        category: str,
        amount: Decimal,
        description: str | None,
        expense_date: date,
        recurrence: str = "none",
        payment_method_id: int | None = None,
    ) -> PersonalExpense:
        recurrence = recurrence or "none"
        group_id = None
        is_origin = False
        if recurrence != "none":
            group_id = str(uuid.uuid4())
            is_origin = True

        expense = PersonalExpense(
            doctor_id=doctor_id,
            category=category,
            amount=amount,
            description=description,
            expense_date=expense_date,
            recurrence=recurrence,
            payment_method_id=payment_method_id,
            recurrence_group_id=group_id,
            is_recurrence_origin=is_origin,
            recurrence_active=True,
        )
        db.add(expense)
        db.commit()
        db.refresh(expense)

        if recurrence != "none":
            ensure_recurring_expenses(db, doctor_id, expense_date.year)
            if expense_date.month >= 11:
                ensure_recurring_expenses(db, doctor_id, expense_date.year + 1)
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
        recurrence: str | None = None,
        payment_method_id: int | None | object = ...,
    ) -> PersonalExpense:
        if category is not None:
            expense.category = category
        if amount is not None:
            expense.amount = amount
        if description is not None:
            expense.description = description
        if expense_date is not None:
            expense.expense_date = expense_date
        if payment_method_id is not ...:
            expense.payment_method_id = payment_method_id  # type: ignore[assignment]
        if recurrence is not None:
            expense.recurrence = recurrence
            if recurrence != "none" and not expense.recurrence_group_id:
                expense.recurrence_group_id = str(uuid.uuid4())
                expense.is_recurrence_origin = True
                expense.recurrence_active = True
            if recurrence == "none" and expense.is_recurrence_origin:
                expense.recurrence_active = False
        db.commit()
        db.refresh(expense)

        if expense.is_recurrence_origin and expense.recurrence_active and expense.recurrence != "none":
            ensure_recurring_expenses(db, expense.doctor_id, expense.expense_date.year)
            if expense.expense_date.month >= 11:
                ensure_recurring_expenses(
                    db, expense.doctor_id, expense.expense_date.year + 1
                )
            db.refresh(expense)

        return expense

    def delete(self, db: Session, expense: PersonalExpense) -> None:
        if expense.is_recurrence_origin and expense.recurrence_group_id:
            # Cancel series: remove future clones and deactivate origin metadata
            db.query(PersonalExpense).filter(
                PersonalExpense.recurrence_group_id == expense.recurrence_group_id,
                PersonalExpense.id != expense.id,
                PersonalExpense.expense_date > expense.expense_date,
            ).delete(synchronize_session=False)
            db.query(PersonalExpense).filter(
                PersonalExpense.recurrence_group_id == expense.recurrence_group_id,
                PersonalExpense.is_recurrence_origin.is_(True),
            ).update(
                {"recurrence_active": False, "recurrence": "none"},
                synchronize_session=False,
            )
        db.delete(expense)
        db.commit()


def ensure_recurring_expenses(db: Session, doctor_id: int, year: int) -> int:
    """Cria lançamentos faltantes das séries ativas até o fim do ano informado."""
    origins = (
        db.query(PersonalExpense)
        .filter(
            PersonalExpense.doctor_id == doctor_id,
            PersonalExpense.is_recurrence_origin.is_(True),
            PersonalExpense.recurrence_active.is_(True),
            PersonalExpense.recurrence != "none",
        )
        .all()
    )
    if not origins:
        return 0

    created = 0

    for origin in origins:
        step = RECURRENCE_MONTH_STEPS.get(origin.recurrence)
        if not step or not origin.recurrence_group_id:
            continue

        group_id = origin.recurrence_group_id
        existing_dates = {
            row.expense_date
            for row in db.query(PersonalExpense.expense_date)
            .filter(PersonalExpense.recurrence_group_id == group_id)
            .all()
        }

        months_ahead = step
        while months_ahead <= 240:
            next_date = add_months(origin.expense_date, months_ahead)
            if next_date.year > year:
                break
            if next_date not in existing_dates:
                db.add(
                    PersonalExpense(
                        doctor_id=origin.doctor_id,
                        category=origin.category,
                        amount=origin.amount,
                        description=origin.description,
                        expense_date=next_date,
                        recurrence=origin.recurrence,
                        payment_method_id=origin.payment_method_id,
                        recurrence_group_id=group_id,
                        is_recurrence_origin=False,
                        recurrence_active=True,
                    )
                )
                existing_dates.add(next_date)
                created += 1
            months_ahead += step

    if created:
        db.commit()
    return created


def list_unified_expenses(
    db: Session,
    doctor_id: int,
    *,
    year: int | None = None,
    month: int | None = None,
    source: str | None = None,
) -> list[dict]:
    if year is not None and source in (None, "personal"):
        ensure_recurring_expenses(db, doctor_id, year)

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


def personal_expense_summary(
    db: Session,
    doctor_id: int,
    *,
    year: int,
    month: int | None = None,
) -> dict:
    ensure_recurring_expenses(db, doctor_id, year)

    query = db.query(PersonalExpense).filter(
        PersonalExpense.doctor_id == doctor_id,
        extract("year", PersonalExpense.expense_date) == year,
    )
    if month is not None:
        query = query.filter(extract("month", PersonalExpense.expense_date) == month)

    expenses = query.options(joinedload(PersonalExpense.payment_method)).all()

    by_category: dict[str, float] = {}
    by_payment: dict[str, dict] = {}

    for expense in expenses:
        cat = expense.category or "other"
        by_category[cat] = by_category.get(cat, 0) + float(expense.amount)

        if expense.payment_method_id and expense.payment_method:
            key = str(expense.payment_method_id)
            entry = by_payment.setdefault(
                key,
                {
                    "id": expense.payment_method_id,
                    "name": expense.payment_method.name,
                    "total": 0.0,
                },
            )
            entry["total"] += float(expense.amount)
        else:
            entry = by_payment.setdefault(
                "none",
                {"id": None, "name": "Não informado", "total": 0.0},
            )
            entry["total"] += float(expense.amount)

    return {
        "year": year,
        "month": month,
        "by_category": [
            {
                "key": key,
                "label": PERSONAL_EXPENSE_CATEGORIES.get(key, key),
                "total": round(total, 2),
            }
            for key, total in sorted(by_category.items(), key=lambda x: -x[1])
        ],
        "by_payment_method": sorted(
            [
                {
                    "id": v["id"],
                    "name": v["name"],
                    "total": round(v["total"], 2),
                }
                for v in by_payment.values()
            ],
            key=lambda x: -x["total"],
        ),
        "total": round(sum(by_category.values()), 2),
    }


__all__ = [
    "PersonalExpenseRepository",
    "PaymentMethodRepository",
    "parse_expense_amount",
    "validate_personal_category",
    "validate_recurrence",
    "list_unified_expenses",
    "ensure_recurring_expenses",
    "personal_expense_summary",
    "add_months",
]
