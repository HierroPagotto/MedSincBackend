from functools import wraps
from flask import request, jsonify
import hashlib
from app.repositories.doctor_repository import DoctorRepository
from app.database import db

doctor_repository = DoctorRepository()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token não fornecido'}), 401

        doctor = None
        for d in db.session.query(doctor_repository.model).all():
            expected_token = hashlib.sha256(f"{d.email}:{d.password}".encode()).hexdigest()
            if token == expected_token:
                doctor = d
                break

        if not doctor:
            return jsonify({'message': 'Token inválido'}), 401

        return f(doctor, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated_function(current_user, *args, **kwargs):
        if not getattr(current_user, 'is_admin', False):
            return jsonify({'message': 'Acesso restrito a administradores'}), 403
        return f(current_user, *args, **kwargs)
    return decorated_function
