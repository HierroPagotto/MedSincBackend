from datetime import datetime
import pytz
from flask import Blueprint, request, jsonify
from app.repositories.shift_repository import ShiftRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.expense_repository import (
    ShiftExpenseRepository,
    parse_expense_amount,
    validate_category,
)
from app.schemas.shift import ShiftCreate, ShiftUpdate
from app.schemas.payment import PaymentCreate
from app.database import db
from app.utils.auth import token_required
from app.models.financial_goal import FinancialGoal
from app.models.shift import SOURCE_MARKETPLACE
from app.models.shift_expense import EXPENSE_CATEGORIES
from app.utils.schedule import doctor_has_conflicting_shift
from app.services.notification_service import notification_service
from sqlalchemy import extract

shift_bp = Blueprint("shift", __name__)
shift_repository = ShiftRepository()
payment_repository = PaymentRepository()
expense_repository = ShiftExpenseRepository()

MARKETPLACE_LOCKED_MSG = (
    "Plantões do marketplace não podem ser editados ou excluídos pelo médico. "
    "Altere pela vaga no hospital, se necessário."
)


def _is_marketplace_shift(shift) -> bool:
    return getattr(shift, "source", None) == SOURCE_MARKETPLACE or bool(
        getattr(shift, "opportunity_id", None)
    )


def _get_owned_shift(current_user, shift_id):
    shift = shift_repository.get_by_id(db.session, shift_id)
    if not shift or shift.doctor_id != current_user.id:
        return None
    return shift


def _notify_conflict_if_any(doctor, shift) -> None:
    try:
        conflict = doctor_has_conflicting_shift(
            db.session,
            doctor_id=doctor.id,
            opportunity_date=shift.date,
            start_time=shift.start_time,
            end_time=shift.end_time,
            exclude_shift_id=shift.id,
        )
        if conflict:
            notification_service.notify_schedule_conflict(
                db.session,
                doctor=doctor,
                shift=shift,
                conflicting=conflict,
            )
    except Exception as exc:
        print(f"Falha ao notificar conflito: {exc}")


@shift_bp.route("/", methods=["POST"])
@token_required
def create_shift(current_user):
    data = request.get_json()

    if "week_days" in data and data["week_days"]:
        shifts = shift_repository.create_multiple_shifts(
            db.session, data, current_user.id
        )

        for shift in shifts:
            payment_data = PaymentCreate(shift_id=shift.id, amount=shift.value)
            payment_repository.create(db.session, payment_data)
            _notify_conflict_if_any(current_user, shift)

        return {"message": f"{len(shifts)} plantões criados com sucesso!"}
    else:
        shift_data = ShiftCreate(**data)
        shift = shift_repository.create(db.session, shift_data, current_user.id)

        payment_data = PaymentCreate(shift_id=shift.id, amount=shift.value)
        payment_repository.create(db.session, payment_data)
        _notify_conflict_if_any(current_user, shift)

        return {"message": "Plantão criado com sucesso!"}


@shift_bp.route("/", methods=["GET"])
@token_required
def get_shifts(current_user):
    shifts = shift_repository.get_by_doctor(db.session, current_user.id)
    shifts_dict = [shift.to_dict() for shift in shifts]
    return jsonify(shifts_dict)


@shift_bp.route("/<int:shift_id>/complete", methods=["POST"])
@token_required
def complete_shift(current_user, shift_id):
    shift = shift_repository.get_by_id(db.session, shift_id)
    if not shift or shift.doctor_id != current_user.id:
        return jsonify({"message": "Plantão não encontrado"}), 404

    shift = shift_repository.update_status(db.session, shift, "completed")

    return {"message": "Atualizado com sucesso!"}


@shift_bp.route("/<int:shift_id>/cancelled", methods=["POST"])
@token_required
def cancelled_shift(current_user, shift_id):
    shift = shift_repository.get_by_id(db.session, shift_id)
    if not shift or shift.doctor_id != current_user.id:
        return jsonify({"message": "Plantão não encontrado"}), 404

    shift = shift_repository.update_status(db.session, shift, "cancelled")

    return {"message": "Atualizado com sucesso!"}


@shift_bp.route("/<int:shift_id>/paid", methods=["POST"])
@token_required
def paid_shift(current_user, shift_id):
    shift = shift_repository.get_by_id(db.session, shift_id)
    if not shift or shift.doctor_id != current_user.id:
        return jsonify({"message": "Plantão não encontrado"}), 404

    shift_repository.update_status(db.session, shift, "paid")

    payment = payment_repository.get_by_shift(db.session, shift_id)
    payment_repository.update_status(db.session, payment, "paid")

    try:
        notification_service.maybe_notify_goal_progress(db.session, current_user)
    except Exception as exc:
        print(f"Falha ao notificar meta: {exc}")

    return {"message": "Atualizado com sucesso!"}


@shift_bp.route("/dashboard", methods=["GET"])
@token_required
def get_dashboard(current_user):
    shifts = shift_repository.get_dashboard_stats(db.session, current_user.id)
    return jsonify(shifts)


@shift_bp.route("/financial", methods=["GET"])
@token_required
def get_financial(current_user):
    shifts = shift_repository.get_financial_chart_data(db.session, current_user.id)
    return jsonify(shifts)


@shift_bp.route("/financial/full", methods=["GET"])
@token_required
def get_financial_full(current_user):
    year = request.args.get("year", type=int)

    if year is None:
        brazil_tz = pytz.timezone("America/Sao_Paulo")
        year = datetime.now(brazil_tz).year

    data = shift_repository.get_financial_data(db.session, current_user.id, year)

    return jsonify(
        {
            "status": "success",
            "data": {
                "monthly_data": data["monthly_data"],
                "annual_totals": data["annual_totals"],
                "year": year,
            },
        }
    )


@shift_bp.route("/<int:shift_id>", methods=["DELETE"])
@token_required
def delete_shift(current_user, shift_id):
    shift = shift_repository.get_by_id(db.session, shift_id)

    if not shift:
        return jsonify({"message": "Plantão não encontrado"}), 404

    if shift.doctor_id != current_user.id:
        return jsonify({"message": "Não autorizado a excluir este plantão"}), 403

    if _is_marketplace_shift(shift):
        return jsonify({"message": MARKETPLACE_LOCKED_MSG}), 403

    if shift.status == "paid":
        return jsonify({"message": "Não é possível excluir um plantão já pago"}), 400

    success = shift_repository.delete_shift(db.session, shift_id)

    if success:
        return jsonify({"message": "Plantão excluído com sucesso"})
    else:
        return jsonify({"message": "Erro ao excluir plantão"}), 500


@shift_bp.route("/bulk_delete", methods=["DELETE"])
@token_required
def bulk_delete_shifts(current_user):
    data = request.get_json()
    ids = data.get("ids", [])
    if not isinstance(ids, list) or not ids:
        return jsonify({"message": "Envie uma lista de IDs para deletar."}), 400
    deleted = []
    not_found = []
    not_allowed = []
    already_paid = []
    marketplace_locked = []
    for shift_id in ids:
        shift = shift_repository.get_by_id(db.session, shift_id)
        if not shift:
            not_found.append(shift_id)
            continue
        if shift.doctor_id != current_user.id:
            not_allowed.append(shift_id)
            continue
        if _is_marketplace_shift(shift):
            marketplace_locked.append(shift_id)
            continue
        if shift.status == "paid":
            already_paid.append(shift_id)
            continue
        success = shift_repository.delete_shift(db.session, shift_id)
        if success:
            deleted.append(shift_id)
    return jsonify(
        {
            "deleted": deleted,
            "not_found": not_found,
            "not_allowed": not_allowed,
            "already_paid": already_paid,
            "marketplace_locked": marketplace_locked,
            "message": f"{len(deleted)} plantões deletados.",
        }
    )


@shift_bp.route("/<int:shift_id>", methods=["PUT"])
@token_required
def update_shift(current_user, shift_id):
    shift = shift_repository.get_by_id(db.session, shift_id)
    if not shift:
        return jsonify({"message": "Plantão não encontrado"}), 404
    if shift.doctor_id != current_user.id:
        return jsonify({"message": "Não autorizado a editar este plantão"}), 403
    if _is_marketplace_shift(shift):
        return jsonify({"message": MARKETPLACE_LOCKED_MSG}), 403
    data = request.get_json()
    update_data = ShiftUpdate(**data)
    previous_date = shift.date
    shift_repository.update(db.session, shift, update_data)
    if shift.date != previous_date:
        expense_repository.sync_dates_for_shift(db.session, shift.id, shift.date)
    _notify_conflict_if_any(current_user, shift)
    return jsonify(
        {"message": "Plantão atualizado com sucesso", "shift": shift.to_dict()}
    )


@shift_bp.route("/expense-categories", methods=["GET"])
@token_required
def list_expense_categories(current_user):
    return jsonify(
        [{"value": key, "label": label} for key, label in EXPENSE_CATEGORIES.items()]
    )


@shift_bp.route("/<int:shift_id>/expenses", methods=["GET"])
@token_required
def list_shift_expenses(current_user, shift_id):
    shift = _get_owned_shift(current_user, shift_id)
    if not shift:
        return jsonify({"message": "Plantão não encontrado"}), 404
    expenses = expense_repository.list_by_shift(db.session, shift_id)
    total = sum(float(e.amount) for e in expenses)
    return jsonify(
        {
            "expenses": [e.to_dict() for e in expenses],
            "expenses_total": total,
            "net_value": float(shift.value) - total,
        }
    )


@shift_bp.route("/<int:shift_id>/expenses", methods=["POST"])
@token_required
def create_shift_expense(current_user, shift_id):
    shift = _get_owned_shift(current_user, shift_id)
    if not shift:
        return jsonify({"message": "Plantão não encontrado"}), 404

    data = request.get_json() or {}
    category = validate_category(data.get("category"))
    if not category:
        return jsonify({"message": "Categoria de gasto inválida"}), 400

    amount = parse_expense_amount(data.get("amount"))
    if amount is None:
        return jsonify({"message": "Valor do gasto deve ser maior que zero"}), 400

    description = data.get("description")
    if description is not None:
        description = str(description).strip()[:255] or None

    expense = expense_repository.create(
        db.session,
        shift_id=shift.id,
        doctor_id=current_user.id,
        category=category,
        amount=amount,
        description=description,
        expense_date=shift.date,
    )
    return jsonify({"message": "Gasto adicionado", "expense": expense.to_dict()}), 201


@shift_bp.route("/<int:shift_id>/expenses/<int:expense_id>", methods=["PUT"])
@token_required
def update_shift_expense(current_user, shift_id, expense_id):
    shift = _get_owned_shift(current_user, shift_id)
    if not shift:
        return jsonify({"message": "Plantão não encontrado"}), 404

    expense = expense_repository.get_by_id(db.session, expense_id)
    if not expense or expense.shift_id != shift.id or expense.doctor_id != current_user.id:
        return jsonify({"message": "Gasto não encontrado"}), 404

    data = request.get_json() or {}
    category = None
    if "category" in data:
        category = validate_category(data.get("category"))
        if not category:
            return jsonify({"message": "Categoria de gasto inválida"}), 400

    amount = None
    if "amount" in data:
        amount = parse_expense_amount(data.get("amount"))
        if amount is None:
            return jsonify({"message": "Valor do gasto deve ser maior que zero"}), 400

    description = expense.description
    if "description" in data:
        raw = data.get("description")
        description = str(raw).strip()[:255] if raw is not None else None
        if description == "":
            description = None

    expense = expense_repository.update(
        db.session,
        expense,
        category=category,
        amount=amount,
        description=description,
        expense_date=shift.date,
    )
    return jsonify({"message": "Gasto atualizado", "expense": expense.to_dict()})


@shift_bp.route("/<int:shift_id>/expenses/<int:expense_id>", methods=["DELETE"])
@token_required
def delete_shift_expense(current_user, shift_id, expense_id):
    shift = _get_owned_shift(current_user, shift_id)
    if not shift:
        return jsonify({"message": "Plantão não encontrado"}), 404

    expense = expense_repository.get_by_id(db.session, expense_id)
    if not expense or expense.shift_id != shift.id or expense.doctor_id != current_user.id:
        return jsonify({"message": "Gasto não encontrado"}), 404

    expense_repository.delete(db.session, expense)
    return jsonify({"message": "Gasto removido"})


# --- Metas financeiras ---
@shift_bp.route("/goal", methods=["GET"])
@token_required
def get_goal(current_user):
    now = datetime.now(pytz.timezone("America/Sao_Paulo"))
    year = int(request.args.get("year", now.year))
    month = int(request.args.get("month", now.month))
    # Meta personalizada
    goal = (
        db.session.query(FinancialGoal)
        .filter_by(user_id=current_user.id, year=year, month=month)
        .first()
    )
    if goal:
        return jsonify(
            {"year": year, "month": month, "value": goal.value, "custom": True}
        )
    # Meta padrão
    default_goal = (
        db.session.query(FinancialGoal)
        .filter_by(user_id=current_user.id, year=0, month=0)
        .first()
    )
    if default_goal:
        return jsonify(
            {"year": year, "month": month, "value": default_goal.value, "custom": False}
        )
    return jsonify({"year": year, "month": month, "value": 0, "custom": False})


@shift_bp.route("/goal", methods=["POST"])
@token_required
def set_goal(current_user):
    data = request.get_json()
    year = int(data.get("year", 0))
    month = int(data.get("month", 0))
    value = float(data.get("value", 0))
    if value <= 0:
        return jsonify({"message": "Valor da meta deve ser maior que zero."}), 400
    goal = (
        db.session.query(FinancialGoal)
        .filter_by(user_id=current_user.id, year=year, month=month)
        .first()
    )
    if not goal:
        goal = FinancialGoal(
            user_id=current_user.id, year=year, month=month, value=value
        )
        db.session.add(goal)
    else:
        goal.value = value
    db.session.commit()
    try:
        notification_service.maybe_notify_goal_progress(db.session, current_user)
    except Exception as exc:
        print(f"Falha ao notificar meta: {exc}")
    return jsonify(
        {
            "message": "Meta salva com sucesso.",
            "goal": {"year": year, "month": month, "value": value},
        }
    )


@shift_bp.route("/goal", methods=["DELETE"])
@token_required
def remove_goal(current_user):
    year = int(request.args.get("year", 0))
    month = int(request.args.get("month", 0))
    goal = (
        db.session.query(FinancialGoal)
        .filter_by(user_id=current_user.id, year=year, month=month)
        .first()
    )
    if not goal:
        return jsonify({"message": "Meta não encontrada."}), 404
    db.session.delete(goal)
    db.session.commit()
    return jsonify({"message": "Meta removida com sucesso."})


@shift_bp.route("/goals", methods=["GET"])
@token_required
def list_goals(current_user):
    goals = db.session.query(FinancialGoal).filter_by(user_id=current_user.id).all()
    return jsonify(
        [{"year": g.year, "month": g.month, "value": g.value} for g in goals]
    )
