from datetime import date

from flask import Blueprint, jsonify, request

from app.database import db
from app.models.attendance import (
    ATTENDANCE_KINDS,
    KIND_PRIVATE,
    KIND_SHIFT,
    PAYMENT_STATUS_OPTIONS,
    VALID_ATTENDANCE_KINDS,
    VALID_PAYMENT_STATUSES,
)
from app.models.shift import Shift
from app.repositories.patient_repository import (
    AttendanceRepository,
    PatientRepository,
    attendance_summary,
    clean_text,
    parse_date,
    parse_positive_amount,
)
from app.utils.auth import token_required

patients_bp = Blueprint("patients", __name__)
patient_repo = PatientRepository()
attendance_repo = AttendanceRepository()


def _error(message: str, status: int = 400):
    return jsonify({"message": message}), status


def _parse_patient_payload(data: dict, partial: bool):
    fields = {}
    if not partial or "name" in data:
        name = clean_text(data.get("name"), 150)
        if not name or len(name) < 2:
            return None, _error("Informe o nome do paciente")
        fields["name"] = name
    if not partial or "birth_date" in data:
        raw = data.get("birth_date")
        if raw in (None, ""):
            fields["birth_date"] = None
        else:
            birth_date = parse_date(raw)
            if not birth_date or birth_date > date.today():
                return None, _error("Data de nascimento inválida")
            fields["birth_date"] = birth_date
    if not partial or "health_plan" in data:
        fields["health_plan"] = clean_text(data.get("health_plan"), 100)
    if partial and "active" in data:
        fields["active"] = bool(data.get("active"))
    return fields, None


def _parse_int(raw):
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


@patients_bp.route("/", methods=["GET"])
@token_required
def list_patients(current_user):
    search = request.args.get("search") or None
    include_inactive = request.args.get("include_inactive") in ("1", "true")
    patients = patient_repo.list_for_doctor(
        db.session, current_user.id, search=search, include_inactive=include_inactive
    )
    counts = patient_repo.attendance_counts(db.session, current_user.id)
    result = []
    for patient in patients:
        item = patient.to_dict()
        item["attendances_count"] = counts.get(patient.id, 0)
        result.append(item)
    return jsonify({"patients": result})


@patients_bp.route("/", methods=["POST"])
@token_required
def create_patient(current_user):
    data = request.get_json() or {}
    fields, err = _parse_patient_payload(data, partial=False)
    if err:
        return err
    patient = patient_repo.create(db.session, current_user.id, **fields)
    item = patient.to_dict()
    item["attendances_count"] = 0
    return jsonify({"message": "Paciente cadastrado", "patient": item}), 201


@patients_bp.route("/<int:patient_id>", methods=["GET"])
@token_required
def get_patient(current_user, patient_id):
    patient = patient_repo.get_owned(db.session, patient_id, current_user.id)
    if not patient:
        return _error("Paciente não encontrado", 404)
    return jsonify({"patient": patient.to_dict(include_attendances=True)})


@patients_bp.route("/<int:patient_id>", methods=["PUT"])
@token_required
def update_patient(current_user, patient_id):
    patient = patient_repo.get_owned(db.session, patient_id, current_user.id)
    if not patient:
        return _error("Paciente não encontrado", 404)
    data = request.get_json() or {}
    fields, err = _parse_patient_payload(data, partial=True)
    if err:
        return err
    patient = patient_repo.update(db.session, patient, **fields)
    return jsonify(
        {
            "message": "Paciente atualizado",
            "patient": patient.to_dict(include_attendances=True),
        }
    )


@patients_bp.route("/<int:patient_id>", methods=["DELETE"])
@token_required
def delete_patient(current_user, patient_id):
    patient = patient_repo.get_owned(db.session, patient_id, current_user.id)
    if not patient:
        return _error("Paciente não encontrado", 404)
    patient_repo.delete(db.session, patient)
    return jsonify({"message": "Paciente e atendimentos excluídos"})


@patients_bp.route("/attendance-options", methods=["GET"])
@token_required
def attendance_options(current_user):
    return jsonify(
        {
            "kinds": [
                {"value": key, "label": label}
                for key, label in ATTENDANCE_KINDS.items()
            ],
            "payment_statuses": [
                {"value": key, "label": label}
                for key, label in PAYMENT_STATUS_OPTIONS.items()
            ],
        }
    )


def _resolve_attendance_fields(data: dict, doctor_id: int, existing=None):
    """Validates the full attendance state (existing values merged with the payload)."""

    def pick(key, default=None):
        if key in data:
            return data.get(key)
        if existing is not None:
            return getattr(existing, key)
        return default

    fields = {}

    patient_id = _parse_int(pick("patient_id"))
    if not patient_id:
        return None, _error("Selecione o paciente")
    if not patient_repo.get_owned(db.session, patient_id, doctor_id):
        return None, _error("Paciente não encontrado")
    fields["patient_id"] = patient_id

    kind = str(pick("kind", KIND_SHIFT) or "").strip()
    if kind not in VALID_ATTENDANCE_KINDS:
        return None, _error("Tipo de atendimento inválido")
    fields["kind"] = kind

    raw_date = pick("date")
    attendance_date = raw_date if isinstance(raw_date, date) else parse_date(raw_date)

    if kind == KIND_SHIFT:
        shift_id = _parse_int(pick("shift_id"))
        if not shift_id:
            return None, _error("Selecione o plantão do atendimento")
        shift = (
            db.session.query(Shift)
            .filter(Shift.id == shift_id, Shift.doctor_id == doctor_id)
            .first()
        )
        if not shift:
            return None, _error("Plantão não encontrado")
        fields["shift_id"] = shift_id
        fields["value"] = None
        fields["payment_status"] = None
        fields["location"] = None
        if not attendance_date:
            attendance_date = shift.date
    else:
        fields["shift_id"] = None
        raw_value = pick("value")
        value = parse_positive_amount(raw_value)
        if value is None:
            return None, _error("Informe o valor da consulta particular")
        fields["value"] = value
        status = str(pick("payment_status", "pending") or "pending").strip()
        if status not in VALID_PAYMENT_STATUSES:
            return None, _error("Status de pagamento inválido")
        fields["payment_status"] = status
        fields["location"] = clean_text(pick("location"), 150)

    if not attendance_date:
        return None, _error("Data do atendimento inválida")
    fields["date"] = attendance_date

    fields["attendance_number"] = clean_text(pick("attendance_number"), 50)
    fields["notes"] = clean_text(pick("notes"), 2000)
    return fields, None


@patients_bp.route("/attendances", methods=["GET"])
@token_required
def list_attendances(current_user):
    kind = request.args.get("kind") or None
    if kind and kind not in VALID_ATTENDANCE_KINDS:
        return _error("Filtro de tipo inválido")
    start_date = parse_date(request.args.get("start_date"))
    end_date = parse_date(request.args.get("end_date"))
    attendances = attendance_repo.list(
        db.session,
        current_user.id,
        patient_id=request.args.get("patient_id", type=int),
        shift_id=request.args.get("shift_id", type=int),
        kind=kind,
        start_date=start_date,
        end_date=end_date,
    )
    private_total = sum(
        float(a.value or 0) for a in attendances if a.kind == KIND_PRIVATE
    )
    return jsonify(
        {
            "attendances": [a.to_dict() for a in attendances],
            "total_count": len(attendances),
            "private_revenue_total": private_total,
        }
    )


@patients_bp.route("/attendances", methods=["POST"])
@token_required
def create_attendance(current_user):
    data = request.get_json() or {}
    fields, err = _resolve_attendance_fields(data, current_user.id)
    if err:
        return err
    attendance = attendance_repo.create(db.session, current_user.id, **fields)
    return (
        jsonify(
            {"message": "Atendimento registrado", "attendance": attendance.to_dict()}
        ),
        201,
    )


@patients_bp.route("/attendances/<int:attendance_id>", methods=["PUT"])
@token_required
def update_attendance(current_user, attendance_id):
    attendance = attendance_repo.get_owned(db.session, attendance_id, current_user.id)
    if not attendance:
        return _error("Atendimento não encontrado", 404)
    data = request.get_json() or {}
    fields, err = _resolve_attendance_fields(data, current_user.id, existing=attendance)
    if err:
        return err
    attendance = attendance_repo.update(db.session, attendance, **fields)
    return jsonify(
        {"message": "Atendimento atualizado", "attendance": attendance.to_dict()}
    )


@patients_bp.route("/attendances/<int:attendance_id>", methods=["DELETE"])
@token_required
def delete_attendance(current_user, attendance_id):
    attendance = attendance_repo.get_owned(db.session, attendance_id, current_user.id)
    if not attendance:
        return _error("Atendimento não encontrado", 404)
    attendance_repo.delete(db.session, attendance)
    return jsonify({"message": "Atendimento excluído"})


@patients_bp.route("/attendances/summary", methods=["GET"])
@token_required
def get_attendance_summary(current_user):
    year = request.args.get("year", type=int) or date.today().year
    return jsonify(attendance_summary(db.session, current_user.id, year))
