from datetime import date, datetime

from flask import Blueprint, jsonify, request

from app.database import db
from app.models.personal_expense import PERSONAL_EXPENSE_CATEGORIES, RECURRENCE_OPTIONS
from app.models.shift_expense import ShiftExpense
from app.repositories.personal_expense_repository import (
    PaymentMethodRepository,
    PersonalExpenseRepository,
    list_unified_expenses,
    parse_expense_amount,
    personal_expense_summary,
    validate_personal_category,
    validate_recurrence,
)
from app.utils.auth import token_required

expenses_bp = Blueprint("expenses", __name__)
personal_repo = PersonalExpenseRepository()
payment_repo = PaymentMethodRepository()


def _parse_expense_date(raw) -> date | None:
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _resolve_payment_method_id(data, doctor_id: int):
    if "payment_method_id" not in data:
        return ..., None
    raw = data.get("payment_method_id")
    if raw is None or raw == "":
        return None, None
    try:
        method_id = int(raw)
    except (TypeError, ValueError):
        return None, (jsonify({"message": "Forma de cobrança inválida"}), 400)
    method = payment_repo.get_usable(db.session, method_id, doctor_id)
    if not method:
        return None, (jsonify({"message": "Forma de cobrança não encontrada"}), 400)
    return method_id, None


@expenses_bp.route("/categories", methods=["GET"])
@token_required
def list_categories(current_user):
    return jsonify(
        [
            {"value": key, "label": label}
            for key, label in PERSONAL_EXPENSE_CATEGORIES.items()
        ]
    )


@expenses_bp.route("/recurrences", methods=["GET"])
@token_required
def list_recurrences(current_user):
    return jsonify(
        [{"value": key, "label": label} for key, label in RECURRENCE_OPTIONS.items()]
    )


@expenses_bp.route("/payment-methods", methods=["GET"])
@token_required
def list_payment_methods(current_user):
    methods = payment_repo.list_for_doctor(db.session, current_user.id)
    return jsonify({"payment_methods": [m.to_dict() for m in methods]})


@expenses_bp.route("/payment-methods", methods=["POST"])
@token_required
def create_payment_method(current_user):
    data = request.get_json() or {}
    name = str(data.get("name") or "").strip()
    if len(name) < 2:
        return jsonify({"message": "Informe um nome com pelo menos 2 caracteres"}), 400
    method = payment_repo.create_custom(
        db.session, doctor_id=current_user.id, name=name
    )
    return jsonify({"message": "Forma de cobrança criada", "payment_method": method.to_dict()}), 201


@expenses_bp.route("/payment-methods/<int:method_id>", methods=["DELETE"])
@token_required
def delete_payment_method(current_user, method_id):
    method = payment_repo.get_by_id(db.session, method_id)
    if not method or not method.is_active:
        return jsonify({"message": "Forma de cobrança não encontrada"}), 404
    if method.doctor_id is None:
        return jsonify({"message": "Formas genéricas não podem ser excluídas"}), 403
    if method.doctor_id != current_user.id:
        return jsonify({"message": "Forma de cobrança não encontrada"}), 404
    payment_repo.delete_custom(db.session, method)
    return jsonify({"message": "Forma de cobrança removida"})


@expenses_bp.route("/summary", methods=["GET"])
@token_required
def expenses_summary(current_user):
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    if year is None:
        year = date.today().year
    if month is not None and (month < 1 or month > 12):
        return jsonify({"message": "Mês inválido"}), 400
    summary = personal_expense_summary(
        db.session, current_user.id, year=year, month=month
    )
    return jsonify(summary)


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

    recurrence = validate_recurrence(data.get("recurrence", "none"))
    if recurrence is None:
        return jsonify({"message": "Recorrência inválida"}), 400

    payment_method_id, err = _resolve_payment_method_id(data, current_user.id)
    if err:
        return err
    if payment_method_id is ...:
        payment_method_id = None

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
        recurrence=recurrence,
        payment_method_id=payment_method_id,
    )
    expense = personal_repo.get_by_id(db.session, expense.id)
    return jsonify({"message": "Gasto adicionado", "expense": expense.to_dict()}), 201


@expenses_bp.route("/<int:expense_id>", methods=["PUT"])
@token_required
def update_expense(current_user, expense_id):
    expense = personal_repo.get_by_id(db.session, expense_id)
    if not expense or expense.doctor_id != current_user.id:
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
                {"message": "Gastos de plantão só podem ser alterados no plantão"}
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

    recurrence = None
    if "recurrence" in data:
        recurrence = validate_recurrence(data.get("recurrence"))
        if recurrence is None:
            return jsonify({"message": "Recorrência inválida"}), 400

    payment_method_id = ...
    if "payment_method_id" in data:
        payment_method_id, err = _resolve_payment_method_id(data, current_user.id)
        if err:
            return err

    expense = personal_repo.update(
        db.session,
        expense,
        category=category,
        amount=amount,
        description=description,
        expense_date=expense_date,
        recurrence=recurrence,
        payment_method_id=payment_method_id,
    )
    expense = personal_repo.get_by_id(db.session, expense.id)
    return jsonify({"message": "Gasto atualizado", "expense": expense.to_dict()})


@expenses_bp.route("/<int:expense_id>", methods=["DELETE"])
@token_required
def delete_expense(current_user, expense_id):
    expense = personal_repo.get_by_id(db.session, expense_id)
    if not expense or expense.doctor_id != current_user.id:
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
                {"message": "Gastos de plantão só podem ser excluídos no plantão"}
            ), 403
        return jsonify({"message": "Gasto não encontrado"}), 404

    personal_repo.delete(db.session, expense)
    return jsonify({"message": "Gasto excluído"})
