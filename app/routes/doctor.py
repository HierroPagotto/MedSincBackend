from datetime import datetime
import uuid
from flask import Blueprint, request, jsonify, send_from_directory
from app.repositories.doctor_repository import DoctorRepository
from app.schemas.doctor import DoctorCreate, DoctorUpdate
from app.database import db
from app.utils.auth import token_required
import os
from werkzeug.utils import secure_filename

doctor_bp = Blueprint("doctor", __name__)
doctor_repository = DoctorRepository()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@doctor_bp.route("/info/<int:doctor_id>", methods=["GET"])
def get_doctor(doctor_id):
    doctor = doctor_repository.get_by_id(db.session, doctor_id)
    if not doctor:
        return jsonify({"message": "Médico não encontrado"}), 404
    return jsonify(doctor.to_dict(include_shifts_count=True))


@doctor_bp.route("/", methods=["POST"])
def create_doctor():
    from dataclasses import fields
    from sqlalchemy.exc import IntegrityError

    from app.repositories.user_repository import UserRepository

    data = request.get_json() or {}
    if data.get("email"):
        data = {**data, "email": str(data["email"]).strip().lower()}

    required = ("name", "email", "password", "main_specialty")
    missing = [f for f in required if not str(data.get(f) or "").strip()]
    if missing:
        return (
            jsonify({"message": "Dados incompletos", "missing": missing}),
            400,
        )

    for key in ("crm", "crm_state", "city", "phone", "state"):
        if key in data and (data[key] is None or str(data[key]).strip() == ""):
            data[key] = None

    allowed = {f.name for f in fields(DoctorCreate)}
    payload = {k: v for k, v in data.items() if k in allowed}

    try:
        doctor_data = DoctorCreate(**payload)
    except TypeError:
        return jsonify({"message": "Dados inválidos"}), 400

    user_repository = UserRepository()

    if doctor_repository.get_by_email(
        db.session, doctor_data.email
    ) or user_repository.get_by_email(db.session, doctor_data.email):
        return jsonify({"message": "Email já cadastrado"}), 400

    try:
        doctor_repository.create(db.session, doctor_data)
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "Não foi possível criar a conta"}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"message": "Erro ao criar conta"}), 500

    return jsonify({"message": "Criado com sucesso!"})


@doctor_bp.route("/me", methods=["GET"])
@token_required
def get_current_doctor(current_user):
    return jsonify(current_user.to_dict(include_shifts_count=True))


@doctor_bp.route("/me", methods=["PUT"])
@token_required
def update_doctor(current_user):
    data = request.get_json()
    update_data = DoctorUpdate(**data)

    doctor_repository.update(db.session, current_user, update_data)
    return {"message": "Atualizado com sucesso!"}


@doctor_bp.route("/upload-photo", methods=["POST"])
def upload_photo():
    if "photo" not in request.files or (file := request.files["photo"]).filename == "":
        return jsonify({"error": "Nenhum arquivo válido enviado"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
    if ext not in {"png", "jpg", "jpeg", "gif", "webp"}:
        return jsonify({"error": "Tipo de arquivo não permitido"}), 400

    unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}.{ext}"
    safe_name = secure_filename(unique_name)
    file.save(os.path.join(UPLOAD_FOLDER, safe_name))

    return jsonify({"photo_url": f"{request.host_url}/static/uploads/{safe_name}"})
