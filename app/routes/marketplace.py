from flask import Blueprint, request, jsonify

from app.database import db
from app.models.shift_opportunity import STATUS_OPEN, STATUS_CANCELLED
from app.models.opportunity_application import STATUS_PENDING, STATUS_WITHDRAWN
from app.schemas.marketplace import OpportunityCreate, OpportunityUpdate
from app.repositories.opportunity_repository import OpportunityRepository
from app.repositories.application_repository import ApplicationRepository
from app.services.marketplace_service import (
    MarketplaceService,
    parse_date,
    parse_time,
)
from app.utils.auth import token_required, hospital_staff_required

marketplace_bp = Blueprint("marketplace", __name__)
opportunity_repo = OpportunityRepository()
application_repo = ApplicationRepository()
marketplace_service = MarketplaceService()


def _parse_opportunity_payload(data: dict, *, partial: bool = False):
    try:
        if partial:
            payload = {}
            if "date" in data:
                payload["date"] = parse_date(data.get("date"))
            if "start_time" in data:
                payload["start_time"] = parse_time(data.get("start_time"))
            if "end_time" in data:
                payload["end_time"] = parse_time(data.get("end_time"))
            if "specialty" in data:
                payload["specialty"] = data.get("specialty")
            if "value" in data:
                payload["value"] = float(data.get("value"))
            if "payment_date" in data:
                payload["payment_date"] = parse_date(data.get("payment_date"))
            if "city" in data:
                payload["city"] = data.get("city")
            if "slots_total" in data:
                payload["slots_total"] = int(data.get("slots_total"))
            if "notes" in data:
                payload["notes"] = data.get("notes")
            return OpportunityUpdate(**payload), None

        required = ["date", "start_time", "end_time", "specialty", "value", "payment_date"]
        missing = [f for f in required if data.get(f) in (None, "")]
        if missing:
            return None, (
                jsonify({"message": "Dados incompletos", "missing": missing}),
                400,
            )

        create = OpportunityCreate(
            date=parse_date(data.get("date")),
            start_time=parse_time(data.get("start_time")),
            end_time=parse_time(data.get("end_time")),
            specialty=data.get("specialty"),
            value=float(data.get("value")),
            payment_date=parse_date(data.get("payment_date")),
            city=data.get("city"),
            slots_total=int(data.get("slots_total") or 1),
            notes=data.get("notes"),
        )
        if create.slots_total < 1:
            return None, (jsonify({"message": "slots_total deve ser >= 1"}), 400)
        if create.payment_date and create.date and create.payment_date < create.date:
            return None, (
                jsonify(
                    {
                        "message": "A data prevista de pagamento não pode ser anterior à data do plantão"
                    }
                ),
                400,
            )
        return create, None
    except (TypeError, ValueError) as exc:
        return None, (jsonify({"message": f"Payload inválido: {exc}"}), 400)


# -------- Médico: listar vagas abertas --------
@marketplace_bp.route("/opportunities", methods=["GET"])
@token_required
def list_open_opportunities(current_doctor):
    city = request.args.get("city")
    specialty = request.args.get("specialty")
    verified_only = request.args.get("verified_only", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    try:
        date_from = parse_date(request.args.get("date_from"))
        date_to = parse_date(request.args.get("date_to"))
        page = int(request.args.get("page") or 1)
        per_page = int(request.args.get("per_page") or 20)
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400

    items, total = opportunity_repo.list_open(
        db.session,
        city=city,
        specialty=specialty,
        date_from=date_from,
        date_to=date_to,
        verified_only=verified_only,
        page=page,
        per_page=per_page,
    )
    return jsonify(
        {
            "count": len(items),
            "total": total,
            "page": page,
            "per_page": per_page,
            "opportunities": [o.to_dict(include_hospital=True) for o in items],
        }
    )


# -------- Hospital: listar vagas do hospital --------
@marketplace_bp.route("/opportunities/mine", methods=["GET"])
@hospital_staff_required
def list_hospital_opportunities(staff):
    status = request.args.get("status")
    items = opportunity_repo.list_by_hospital(
        db.session, staff.hospital_id, status=status
    )
    return jsonify(
        {
            "count": len(items),
            "opportunities": [
                o.to_dict(include_hospital=True, include_applications_count=True)
                for o in items
            ],
        }
    )


@marketplace_bp.route("/opportunities", methods=["POST"])
@hospital_staff_required
def create_opportunity(staff):
    data = request.get_json() or {}
    payload, error = _parse_opportunity_payload(data, partial=False)
    if error:
        return error

    if not payload.city:
        from app.models.hospital import Hospital

        hospital = (
            db.session.query(Hospital).filter(Hospital.id == staff.hospital_id).first()
        )
        if hospital and hospital.city:
            payload.city = hospital.city

    opportunity = opportunity_repo.create(
        db.session,
        hospital_id=staff.hospital_id,
        created_by_staff_id=staff.id,
        data=payload,
    )
    return (
        jsonify(
            {
                "message": "Oportunidade publicada",
                "opportunity": opportunity.to_dict(include_hospital=True),
            }
        ),
        201,
    )


@marketplace_bp.route("/opportunities/<int:opportunity_id>", methods=["GET"])
def get_opportunity(opportunity_id):
    """Detalhe público se open; staff do hospital ou médico autenticado também veem filled."""
    opportunity = opportunity_repo.get_by_id(db.session, opportunity_id)
    if not opportunity:
        return jsonify({"message": "Oportunidade não encontrada"}), 404

    # Sem auth: só open
    auth_header = request.headers.get("Authorization")
    if not auth_header and opportunity.status != STATUS_OPEN:
        return jsonify({"message": "Oportunidade não encontrada"}), 404

    return jsonify(
        opportunity.to_dict(include_hospital=True, include_applications_count=True)
    )


@marketplace_bp.route("/opportunities/<int:opportunity_id>", methods=["PUT"])
@hospital_staff_required
def update_opportunity(staff, opportunity_id):
    opportunity = opportunity_repo.get_by_id(db.session, opportunity_id)
    if not opportunity or opportunity.hospital_id != staff.hospital_id:
        return jsonify({"message": "Oportunidade não encontrada"}), 404
    if opportunity.status != STATUS_OPEN:
        return (
            jsonify({"message": "Somente oportunidades abertas podem ser editadas"}),
            400,
        )

    data = request.get_json() or {}
    payload, error = _parse_opportunity_payload(data, partial=True)
    if error:
        return error

    next_date = payload.date if payload.date is not None else opportunity.date
    next_payment = (
        payload.payment_date
        if payload.payment_date is not None
        else opportunity.payment_date
    )
    if next_payment and next_date and next_payment < next_date:
        return (
            jsonify(
                {
                    "message": "A data prevista de pagamento não pode ser anterior à data do plantão"
                }
            ),
            400,
        )

    updated = opportunity_repo.update(db.session, opportunity, payload)
    return jsonify(
        {
            "message": "Oportunidade atualizada",
            "opportunity": updated.to_dict(include_hospital=True),
        }
    )


@marketplace_bp.route("/opportunities/<int:opportunity_id>/cancel", methods=["POST"])
@hospital_staff_required
def cancel_opportunity(staff, opportunity_id):
    opportunity = opportunity_repo.get_by_id(db.session, opportunity_id)
    if not opportunity or opportunity.hospital_id != staff.hospital_id:
        return jsonify({"message": "Oportunidade não encontrada"}), 404
    if opportunity.status == STATUS_CANCELLED:
        return jsonify({"message": "Oportunidade já cancelada"}), 400

    cancelled = opportunity_repo.cancel(db.session, opportunity)
    return jsonify(
        {
            "message": "Oportunidade cancelada",
            "opportunity": cancelled.to_dict(include_hospital=True),
        }
    )


@marketplace_bp.route("/opportunities/<int:opportunity_id>/apply", methods=["POST"])
@token_required
def apply_to_opportunity(current_doctor, opportunity_id):
    from app.utils.schedule import doctor_has_conflicting_shift
    from app.utils.marketplace_notifications import notify_hospital_new_application
    from app.services.notification_service import notification_service

    opportunity = opportunity_repo.get_by_id(db.session, opportunity_id)
    if not opportunity:
        return jsonify({"message": "Oportunidade não encontrada"}), 404
    if opportunity.status != STATUS_OPEN or opportunity.slots_remaining <= 0:
        return (
            jsonify({"message": "Oportunidade não está aberta para candidaturas"}),
            400,
        )

    conflict = doctor_has_conflicting_shift(
        db.session,
        doctor_id=current_doctor.id,
        opportunity_date=opportunity.date,
        start_time=opportunity.start_time,
        end_time=opportunity.end_time,
    )
    if conflict:
        return (
            jsonify(
                {
                    "message": "Você já possui plantão conflitante neste horário",
                    "conflicting_shift_id": conflict.id,
                }
            ),
            409,
        )

    existing = application_repo.get_by_opportunity_and_doctor(
        db.session, opportunity_id, current_doctor.id
    )
    if existing and existing.status not in (STATUS_WITHDRAWN,):
        return (
            jsonify(
                {
                    "message": "Você já se candidatou a esta oportunidade",
                    "application": existing.to_dict(),
                }
            ),
            409,
        )

    data = request.get_json(silent=True) or {}
    message = data.get("message")

    if existing and existing.status == STATUS_WITHDRAWN:
        existing.status = STATUS_PENDING
        existing.message = message
        existing.reviewed_by_staff_id = None
        existing.reviewed_at = None
        db.session.commit()
        db.session.refresh(existing)
        application = existing
    else:
        application = application_repo.create(
            db.session,
            opportunity_id=opportunity_id,
            doctor_id=current_doctor.id,
            message=message,
        )

    notify_hospital_new_application(opportunity=opportunity, doctor=current_doctor)
    try:
        notification_service.notify_new_application(
            db.session,
            opportunity=opportunity,
            doctor=current_doctor,
            application_id=application.id,
        )
    except Exception as exc:
        print(f"Falha notificação in-app nova candidatura: {exc}")

    return (
        jsonify(
            {
                "message": "Candidatura enviada",
                "application": application.to_dict(include_opportunity=True),
            }
        ),
        201,
    )


@marketplace_bp.route(
    "/opportunities/<int:opportunity_id>/applications", methods=["GET"]
)
@hospital_staff_required
def list_opportunity_applications(staff, opportunity_id):
    opportunity = opportunity_repo.get_by_id(db.session, opportunity_id)
    if not opportunity or opportunity.hospital_id != staff.hospital_id:
        return jsonify({"message": "Oportunidade não encontrada"}), 404

    apps = application_repo.list_by_opportunity(db.session, opportunity_id)
    return jsonify(
        {
            "count": len(apps),
            "applications": [a.to_dict(include_doctor=True) for a in apps],
        }
    )


@marketplace_bp.route("/applications/mine", methods=["GET"])
@token_required
def list_my_applications(current_doctor):
    apps = application_repo.list_by_doctor(db.session, current_doctor.id)
    return jsonify(
        {
            "count": len(apps),
            "applications": [a.to_dict(include_opportunity=True) for a in apps],
        }
    )


@marketplace_bp.route("/applications/<int:application_id>/withdraw", methods=["POST"])
@token_required
def withdraw_application(current_doctor, application_id):
    application = application_repo.get_by_id(db.session, application_id)
    if not application or application.doctor_id != current_doctor.id:
        return jsonify({"message": "Candidatura não encontrada"}), 404
    if application.status != STATUS_PENDING:
        return (
            jsonify({"message": "Somente candidaturas pendentes podem ser retiradas"}),
            400,
        )

    updated = application_repo.withdraw(db.session, application)
    return jsonify(
        {
            "message": "Candidatura retirada",
            "application": updated.to_dict(include_opportunity=True),
        }
    )


@marketplace_bp.route("/applications/<int:application_id>/approve", methods=["POST"])
@hospital_staff_required
def approve_application(staff, application_id):
    result, error = marketplace_service.approve_application(
        db.session, application_id=application_id, staff=staff
    )
    if error:
        body, code = error
        return jsonify(body), code
    return jsonify(result)


@marketplace_bp.route("/applications/<int:application_id>/reject", methods=["POST"])
@hospital_staff_required
def reject_application(staff, application_id):
    result, error = marketplace_service.reject_application(
        db.session, application_id=application_id, staff=staff
    )
    if error:
        body, code = error
        return jsonify(body), code
    return jsonify(result)
