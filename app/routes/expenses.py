from datetime import date, datetime

from flask import Blueprint, jsonify, request

from app.database import db
from app.models.personal_expense import PERSONAL_EXPENSE_CATEGORIES
from app.repositories.personal_expense_repository import (
    PersonalExpenseRepository,
    list_unified_expenses,
    parse_expense_amount,
    validate_personal_category,
)
from app.utils.auth import token_required

expenses_bp = Blueprint("expenses", __name__)
personal_repo = PersonalExpenseRepository()


def _parse_expense_date(raw) -> date | None:
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


@expenses_bp.route("/categories", methods=["GET"])
@token_required
def list_categories(current_user):
    return jsonify(
        [
            {"value": key, "label": label}
            for key, label in PERSONAL_EXPENSE_CATEGORIES.items()
        ]
    )


@expenses_bp.route("/", methods=["GET"])
@token_required
def list_expenses(current_user):
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    source = request.args.get("source")
    if source and source not in ("personal", "shift"):
        return jsonify({"message": "Filtro source inválido"}), 400
    if month is not None and (month < 1 or month > 12):
        return jsonify({"message": "Mês inválido"}), 400

    expenses = list_unified_expenses(
        db.session,
        current_user.id,
        year=year,
        month=month,
        source=source,
    )
    total = sum(float(e.get("amount") or 0) for e in expenses)
    return jsonify({"expenses": expenses, "expenses_total": total})


@expenses_bp.route("/", methods=["POST"])
@token_required
def create_expense(current_user):
    data = request.get_json() or {}
    category = validate_personal_category(data.get("category"))
    if not category:
        return jsonify({"message": "Categoria de gasto inválida"}), 400

    amount = parse_expense_amount(data.get("amount"))
    if amount is None:
        return jsonify({"message": "Valor do gasto deve ser maior que zero"}), 400

    expense_date = _parse_expense_date(data.get("expense_date"))
    if not expense_date:
        return jsonify({"message": "Data do gasto inválida"}), 400

    description = data.get("description")
    if description is not None:
        description = str(description).strip()[:255] or None

    expense = personal_repo.create(
        db.session,
        doctor_id=current_user.id,
        category=category,
        amount=amount,
        description=description,
        expense_date=expense_date,
    )
    return jsonify({"message": "Gasto adicionado", "expense": expense.to_dict()}), 201


@expenses_bp.route("/<int:expense_id>", methods=["PUT"])
@token_required
def update_expense(current_user, expense_id):
    expense = personal_repo.get_by_id(db.session, expense_id)
    if not expense or expense.doctor_id != current_user.id:
        from app.models.shift_expense import ShiftExpense

        shift_expense = (
            db.session.query(ShiftExpense)
            .filter(
                ShiftExpense.id == expense_id,
                ShiftExpense.doctor_id == current_user.id,
            )
            .first()
        )
        if shift_expense:
            return jsonify(
                {
                    "message": "Gastos de plantão só podem ser alterados no plantão"
                }
            ), 403
        return jsonify({"message": "Gasto não encontrado"}), 404

    data = request.get_json() or {}
    category = None
    if "category" in data:
        category = validate_personal_category(data.get("category"))
        if not category:
            return jsonify({"message": "Categoria de gasto inválida"}), 400

    amount = None
    if "amount" in data:
        amount = parse_expense_amount(data.get("amount"))
        if amount is None:
            return jsonify({"message": "Valor do gasto deve ser maior que zero"}), 400

    expense_date = None
    if "expense_date" in data:
        expense_date = _parse_expense_date(data.get("expense_date"))
        if not expense_date:
            return jsonify({"message": "Data do gasto inválida"}), 400

    description = expense.description
    if "description" in data:
        raw = data.get("description")
        description = str(raw).strip()[:255] if raw is not None else None
        if description == "":
            description = None

    expense = personal_repo.update(
        db.session,
        expense,
        category=category,
        amount=amount,
        description=description,
        expense_date=expense_date,
    )
    return jsonify({"message": "Gasto atualizado", "expense": expense.to_dict()})


@expenses_bp.route("/<int:expense_id>", methods=["DELETE"])
@token_required
def delete_expense(current_user, expense_id):
    expense = personal_repo.get_by_id(db.session, expense_id)
    if not expense or expense.doctor_id != current_user.id:
        from app.models.shift_expense import ShiftExpense

        shift_expense = (
            db.session.query(ShiftExpense)
            .filter(
                ShiftExpense.id == expense_id,
                ShiftExpense.doctor_id == current_user.id,
            )
            .first()
        )
        if shift_expense:
            return jsonify(
                {
                    "message": "Gastos de plantão só podem ser excluídos no plantão"
                }
            ), 403
        return jsonify({"message": "Gasto não encontrado"}), 404

    personal_repo.delete(db.session, expense)
    return jsonify({"message": "Gasto excluído"})
