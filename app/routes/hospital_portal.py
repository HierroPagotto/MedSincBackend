from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta

from app.database import db
from app.models.hospital import Hospital
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.repositories.hospital_staff_repository import HospitalStaffRepository
from app.utils.auth import hospital_staff_required, hospital_admin_required
from app.utils.security import (
    ROLE_HOSPITAL_STAFF,
    STAFF_ADMIN,
    STAFF_RECRUITER,
    create_access_token,
)

hospital_portal_bp = Blueprint("hospital_portal", __name__)
user_repository = UserRepository()
staff_repository = HospitalStaffRepository()

ALLOWED_STAFF_ROLES = {STAFF_ADMIN, STAFF_RECRUITER}


@hospital_portal_bp.route("/auth/hospital/register", methods=["POST"])
def register_hospital():
    data = request.get_json() or {}
    hospital_data = data.get("hospital") or {}
    admin_data = data.get("admin") or {}

    required_hospital = ["name", "address", "latitude", "longitude"]
    required_admin = ["name", "email", "password"]

    missing_h = [f for f in required_hospital if hospital_data.get(f) is None]
    missing_a = [f for f in required_admin if not admin_data.get(f)]
    if missing_h or missing_a:
        return (
            jsonify(
                {
                    "message": "Dados incompletos",
                    "missing_hospital": missing_h,
                    "missing_admin": missing_a,
                }
            ),
            400,
        )

    if not data.get("accepted_terms"):
        return jsonify(
            {
                "message": "É necessário aceitar a Política de Privacidade e os Termos de Uso"
            }
        ), 400

    email = admin_data["email"].strip().lower()
    if user_repository.get_by_email(db.session, email):
        return jsonify({"message": "Email já cadastrado"}), 400

    hospital = Hospital(
        name=hospital_data["name"],
        address=hospital_data["address"],
        latitude=hospital_data["latitude"],
        longitude=hospital_data["longitude"],
        city=hospital_data.get("city"),
        state=hospital_data.get("state"),
        cnpj=hospital_data.get("cnpj"),
        is_verified=False,
    )
    db.session.add(hospital)
    db.session.flush()

    user = user_repository.create(
        db.session,
        email=email,
        password=admin_data["password"],
        role=ROLE_HOSPITAL_STAFF,
        commit=False,
    )

    staff = staff_repository.create(
        db.session,
        user_id=user.id,
        hospital_id=hospital.id,
        staff_role=STAFF_ADMIN,
        name=admin_data["name"],
        phone=admin_data.get("phone"),
        commit=False,
    )

    db.session.commit()

    token = create_access_token(
        user_id=user.id,
        role=ROLE_HOSPITAL_STAFF,
        staff_id=staff.id,
        hospital_id=hospital.id,
        staff_role=STAFF_ADMIN,
    )

    return (
        jsonify(
            {
                "message": "Hospital cadastrado com sucesso",
                "token": token,
                "role": ROLE_HOSPITAL_STAFF,
                "name": staff.name,
                "staff_id": staff.id,
                "hospital_id": hospital.id,
                "staff_role": STAFF_ADMIN,
                "email": user.email,
                "hospital": hospital.to_dict(),
            }
        ),
        201,
    )


@hospital_portal_bp.route("/hospital/me", methods=["GET"])
@hospital_staff_required
def hospital_me(staff):
    data = staff.to_dict(include_hospital=True, include_user=True)
    data["role"] = ROLE_HOSPITAL_STAFF
    return jsonify(data)


@hospital_portal_bp.route("/hospital/staff", methods=["GET"])
@hospital_staff_required
def list_staff(staff):
    members = staff_repository.list_by_hospital(db.session, staff.hospital_id)
    return jsonify(
        {
            "count": len(members),
            "staff": [m.to_dict(include_user=True) for m in members],
        }
    )


@hospital_portal_bp.route("/hospital/staff", methods=["POST"])
@hospital_admin_required
def create_staff(staff):
    data = request.get_json() or {}
    name = data.get("name")
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    phone = data.get("phone")
    staff_role = data.get("staff_role", STAFF_RECRUITER)

    if not name or not email or not password:
        return jsonify({"message": "name, email e password são obrigatórios"}), 400

    if staff_role not in ALLOWED_STAFF_ROLES:
        return (
            jsonify(
                {
                    "message": f"staff_role inválido. Use: {', '.join(sorted(ALLOWED_STAFF_ROLES))}"
                }
            ),
            400,
        )

    if user_repository.get_by_email(db.session, email):
        return jsonify({"message": "Email já cadastrado"}), 400

    user = user_repository.create(
        db.session,
        email=email,
        password=password,
        role=ROLE_HOSPITAL_STAFF,
        commit=False,
    )
    member = staff_repository.create(
        db.session,
        user_id=user.id,
        hospital_id=staff.hospital_id,
        staff_role=staff_role,
        name=name,
        phone=phone,
        commit=False,
    )
    db.session.commit()

    return (
        jsonify(
            {
                "message": "Colaborador criado com sucesso",
                "staff": member.to_dict(include_user=True),
            }
        ),
        201,
    )


@hospital_portal_bp.route("/hospital/staff/<int:staff_id>", methods=["DELETE"])
@hospital_admin_required
def deactivate_staff(current_staff, staff_id):
    if current_staff.id == staff_id:
        return jsonify({"message": "Não é possível desativar a si mesmo"}), 400

    member = staff_repository.get_by_id(db.session, staff_id)
    if not member or member.hospital_id != current_staff.hospital_id:
        return jsonify({"message": "Colaborador não encontrado"}), 404

    user = db.session.query(User).filter(User.id == member.user_id).first()
    if user:
        user.is_active = False
        db.session.commit()

    return jsonify({"message": "Colaborador desativado com sucesso"})
