from functools import wraps

import jwt
from flask import request, jsonify

from app.database import db
from app.models.user import User
from app.models.doctor import Doctor
from app.models.hospital_staff import HospitalStaff
from app.utils.security import (
    decode_access_token,
    ROLE_DOCTOR,
    ROLE_HOSPITAL_STAFF,
    ROLE_PLATFORM_ADMIN,
    STAFF_ADMIN,
)


def extract_bearer_token(header_value: str | None) -> str | None:
    if not header_value:
        return None
    value = header_value.strip()
    if value.lower().startswith("bearer "):
        return value[7:].strip()
    return value


def _load_user_from_token():
    raw = extract_bearer_token(request.headers.get("Authorization"))
    if not raw:
        return None, (jsonify({"message": "Token não fornecido"}), 401)

    try:
        payload = decode_access_token(raw)
    except jwt.ExpiredSignatureError:
        return None, (jsonify({"message": "Token expirado"}), 401)
    except jwt.InvalidTokenError:
        return None, (jsonify({"message": "Token inválido"}), 401)

    user_id = payload.get("sub")
    if not user_id:
        return None, (jsonify({"message": "Token inválido"}), 401)

    user = db.session.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        return None, (jsonify({"message": "Usuário inativo ou não encontrado"}), 401)

    return (user, payload), None


def token_required(f):
    """Exige usuário médico (ou platform_admin com perfil doctor). Injeta Doctor."""

    @wraps(f)
    def decorated(*args, **kwargs):
        loaded, error = _load_user_from_token()
        if error:
            return error

        user, payload = loaded
        if user.role not in (ROLE_DOCTOR, ROLE_PLATFORM_ADMIN):
            return jsonify({"message": "Acesso restrito a profissionais"}), 403

        doctor = None
        doctor_id = payload.get("doctor_id")
        if doctor_id:
            doctor = db.session.query(Doctor).filter(Doctor.id == doctor_id).first()
        if not doctor:
            doctor = db.session.query(Doctor).filter(Doctor.user_id == user.id).first()
        if not doctor:
            return jsonify({"message": "Perfil profissional não encontrado"}), 403

        return f(doctor, *args, **kwargs)

    return decorated


def authenticated_user_required(f):
    """Exige qualquer usuário autenticado ativo. Injeta User."""

    @wraps(f)
    def decorated(*args, **kwargs):
        loaded, error = _load_user_from_token()
        if error:
            return error

        user, _payload = loaded
        return f(user, *args, **kwargs)

    return decorated


def hospital_staff_required(f):
    """Exige hospital_staff. Injeta HospitalStaff."""

    @wraps(f)
    def decorated(*args, **kwargs):
        loaded, error = _load_user_from_token()
        if error:
            return error

        user, payload = loaded
        if user.role != ROLE_HOSPITAL_STAFF:
            return jsonify({"message": "Acesso restrito a gestores hospitalares"}), 403

        staff = None
        staff_id = payload.get("staff_id")
        if staff_id:
            staff = (
                db.session.query(HospitalStaff)
                .filter(HospitalStaff.id == staff_id)
                .first()
            )
        if not staff:
            staff = (
                db.session.query(HospitalStaff)
                .filter(HospitalStaff.user_id == user.id)
                .first()
            )
        if not staff:
            return jsonify({"message": "Perfil de gestor não encontrado"}), 403

        return f(staff, *args, **kwargs)

    return decorated


def hospital_admin_required(f):
    """Exige hospital_staff com role hospital_admin. Injeta HospitalStaff."""

    @wraps(f)
    def decorated(*args, **kwargs):
        loaded, error = _load_user_from_token()
        if error:
            return error

        user, payload = loaded
        if user.role != ROLE_HOSPITAL_STAFF:
            return jsonify({"message": "Acesso restrito a gestores hospitalares"}), 403

        staff = None
        staff_id = payload.get("staff_id")
        if staff_id:
            staff = (
                db.session.query(HospitalStaff)
                .filter(HospitalStaff.id == staff_id)
                .first()
            )
        if not staff:
            staff = (
                db.session.query(HospitalStaff)
                .filter(HospitalStaff.user_id == user.id)
                .first()
            )
        if not staff:
            return jsonify({"message": "Perfil de gestor não encontrado"}), 403
        if staff.staff_role != STAFF_ADMIN:
            return (
                jsonify({"message": "Acesso restrito a administradores do hospital"}),
                403,
            )

        return f(staff, *args, **kwargs)

    return decorated


def admin_required(f):
    @wraps(f)
    def decorated_function(current_user, *args, **kwargs):
        if not getattr(current_user, "is_admin", False):
            return jsonify({"message": "Acesso restrito a administradores"}), 403
        return f(current_user, *args, **kwargs)

    return decorated_function
