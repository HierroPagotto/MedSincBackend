from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta

from app.database import db
from app.repositories.doctor_repository import DoctorRepository
from app.repositories.user_repository import UserRepository
from app.utils.email import send_password_reset_email
from app.utils.passwords import verify_password, hash_password
from app.utils.security import (
    create_access_token,
    ROLE_DOCTOR,
    ROLE_HOSPITAL_STAFF,
    ROLE_PLATFORM_ADMIN,
)
from app.utils.auth import _load_user_from_token
from app.models.user import User
from app.repositories.hospital_staff_repository import HospitalStaffRepository
import random
import string

auth_bp = Blueprint("auth", __name__)
doctor_repository = DoctorRepository()
user_repository = UserRepository()
staff_repository = HospitalStaffRepository()


def _is_code_expired(requested_time) -> bool:
    if not requested_time:
        return True
    requested = requested_time
    if getattr(requested, "tzinfo", None) is not None:
        requested = requested.replace(tzinfo=None)
    return datetime.now() - requested > timedelta(hours=1)


def _login_response_for_user(user: User):
    if not user.is_active:
        return jsonify({"message": "Usuário inativo"}), 403

    if user.role in (ROLE_DOCTOR, ROLE_PLATFORM_ADMIN):
        doctor = doctor_repository.get_by_user_id(db.session, user.id)
        if not doctor:
            doctor = doctor_repository.get_by_email(db.session, user.email)
            if doctor and not doctor.user_id:
                doctor.user_id = user.id
                db.session.commit()
        if not doctor:
            return jsonify({"message": "Perfil de médico não encontrado"}), 403

        token = create_access_token(
            user_id=user.id,
            role=user.role,
            doctor_id=doctor.id,
            is_admin=bool(doctor.is_admin or user.role == ROLE_PLATFORM_ADMIN),
        )
        return jsonify(
            {
                "token": token,
                "role": user.role,
                "name": doctor.name,
                "is_admin": bool(doctor.is_admin or user.role == ROLE_PLATFORM_ADMIN),
                "doctor_id": doctor.id,
                "email": user.email,
            }
        )

    if user.role == ROLE_HOSPITAL_STAFF:
        staff = staff_repository.get_by_user_id(db.session, user.id)
        if not staff:
            return jsonify({"message": "Perfil de gestor não encontrado"}), 403

        token = create_access_token(
            user_id=user.id,
            role=user.role,
            staff_id=staff.id,
            hospital_id=staff.hospital_id,
            staff_role=staff.staff_role,
        )
        return jsonify(
            {
                "token": token,
                "role": user.role,
                "name": staff.name,
                "staff_id": staff.id,
                "hospital_id": staff.hospital_id,
                "staff_role": staff.staff_role,
                "email": user.email,
                "is_admin": False,
            }
        )

    return jsonify({"message": "Tipo de usuário não suportado"}), 403


@auth_bp.route("/login", methods=["POST"])
@auth_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email e senha são obrigatórios"}), 400

    email = email.strip().lower()
    user = user_repository.get_by_email(db.session, email)
    if user and verify_password(password, user.password):
        return _login_response_for_user(user)

    doctor = doctor_repository.get_by_email(db.session, email)
    if doctor and verify_password(password, doctor.password):
        if not doctor.user_id:
            role = ROLE_PLATFORM_ADMIN if doctor.is_admin else ROLE_DOCTOR
            user = user_repository.create(
                db.session,
                email=doctor.email,
                password=doctor.password,
                role=role,
                commit=False,
                already_hashed=True,
            )
            doctor.user_id = user.id
            db.session.commit()
        else:
            user = user_repository.get_by_id(db.session, doctor.user_id)
        if user:
            return _login_response_for_user(user)

    return jsonify({"message": "Credenciais inválidas"}), 401


@auth_bp.route("/auth/me", methods=["GET"])
def auth_me():
    loaded, error = _load_user_from_token()
    if error:
        return error

    user, _payload = loaded
    if user.role in (ROLE_DOCTOR, ROLE_PLATFORM_ADMIN):
        doctor = doctor_repository.get_by_user_id(db.session, user.id)
        if not doctor:
            return jsonify({"message": "Perfil de médico não encontrado"}), 404
        data = doctor.to_dict(include_shifts_count=True)
        data["role"] = user.role
        data["user_id"] = user.id
        return jsonify(data)

    if user.role == ROLE_HOSPITAL_STAFF:
        staff = staff_repository.get_by_user_id(db.session, user.id)
        if not staff:
            return jsonify({"message": "Perfil de gestor não encontrado"}), 404
        data = staff.to_dict(include_hospital=True, include_user=True)
        data["role"] = user.role
        data["user_id"] = user.id
        return jsonify(data)

    return jsonify({"message": "Tipo de usuário não suportado"}), 403


@auth_bp.route("/password-reset/request", methods=["POST"])
def request_password_reset():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()

    doctor = doctor_repository.get_by_email(db.session, email)
    if not doctor:
        return jsonify({"message": "Email não encontrado"}), 404

    code = "".join(random.choices(string.digits, k=6))
    doctor.lost_pass_code = code
    doctor.lost_pass_code_requested_time = datetime.now()
    db.session.commit()

    send_password_reset_email(email, code, doctor.name)

    return jsonify({"message": "Código de recuperação enviado para seu email"})


@auth_bp.route("/password-reset/verify", methods=["POST"])
def verify_password_reset_code():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    code = data.get("code")

    doctor = doctor_repository.get_by_email(db.session, email)
    if not doctor:
        return jsonify({"message": "Email não encontrado"}), 404

    if not doctor.lost_pass_code or not doctor.lost_pass_code_requested_time:
        return jsonify({"message": "Código não solicitado"}), 400

    if _is_code_expired(doctor.lost_pass_code_requested_time):
        return jsonify({"message": "Código expirado"}), 400

    if doctor.lost_pass_code != code:
        return jsonify({"message": "Código inválido"}), 400

    return jsonify({"message": "Código válido", "valid": True})


@auth_bp.route("/password-reset/change", methods=["POST"])
def change_password():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    code = data.get("code")
    new_password = data.get("new_password")

    doctor = doctor_repository.get_by_email(db.session, email)
    if not doctor:
        return jsonify({"message": "Email não encontrado"}), 404

    if not doctor.lost_pass_code or not doctor.lost_pass_code_requested_time:
        return jsonify({"message": "Código não solicitado"}), 400

    if _is_code_expired(doctor.lost_pass_code_requested_time):
        return jsonify({"message": "Código expirado"}), 400

    if doctor.lost_pass_code != code:
        return jsonify({"message": "Código inválido"}), 400

    hashed_password = hash_password(new_password)
    doctor.password = hashed_password
    doctor.lost_pass_code = None
    doctor.lost_pass_code_requested_time = None

    user = None
    if doctor.user_id:
        user = user_repository.get_by_id(db.session, doctor.user_id)
    if not user:
        user = user_repository.get_by_email(db.session, doctor.email)
    if user:
        user.password = hashed_password
        doctor.user_id = user.id

    db.session.commit()

    return jsonify({"message": "Senha alterada com sucesso"})
