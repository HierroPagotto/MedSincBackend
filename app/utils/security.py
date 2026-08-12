import os
from datetime import datetime, timedelta, timezone

import jwt

ROLE_DOCTOR = "doctor"
ROLE_HOSPITAL_STAFF = "hospital_staff"
ROLE_PLATFORM_ADMIN = "platform_admin"

STAFF_ADMIN = "hospital_admin"
STAFF_RECRUITER = "hospital_recruiter"


def _secret_key() -> str:
    key = os.environ.get("SECRET_KEY")
    if not key:
        raise RuntimeError("SECRET_KEY não configurada")
    return key


def _algorithm() -> str:
    return os.environ.get("ALGORITHM", "HS256")


def _expire_minutes() -> int:
    try:
        return int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    except ValueError:
        return 1440


def create_access_token(
    *,
    user_id: int,
    role: str,
    doctor_id: int | None = None,
    staff_id: int | None = None,
    hospital_id: int | None = None,
    staff_role: str | None = None,
    is_admin: bool = False,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "doctor_id": doctor_id,
        "staff_id": staff_id,
        "hospital_id": hospital_id,
        "staff_role": staff_role,
        "is_admin": is_admin,
        "iat": now,
        "exp": now + timedelta(minutes=_expire_minutes()),
    }
    return jwt.encode(payload, _secret_key(), algorithm=_algorithm())


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, _secret_key(), algorithms=[_algorithm()])


# Compatível com imports antigos; preferir create_access_token
def generate_token(doctor):
    user_id = getattr(doctor, "user_id", None) or doctor.id
    return create_access_token(
        user_id=user_id,
        role=ROLE_PLATFORM_ADMIN if getattr(doctor, "is_admin", False) else ROLE_DOCTOR,
        doctor_id=doctor.id,
        is_admin=bool(getattr(doctor, "is_admin", False)),
    )
