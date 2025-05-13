from app.utils.security import generate_token
from flask import Blueprint, request, jsonify
import bcrypt
from app.repositories.doctor_repository import DoctorRepository
from app.database import db

auth_bp = Blueprint('auth', __name__)
doctor_repository = DoctorRepository()

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    doctor = doctor_repository.get_by_email(db.session, email)
    if not doctor or not bcrypt.checkpw(password.encode(), doctor.password.encode()):
        return jsonify({'message': 'Credenciais inválidas'}), 401

    token = generate_token(doctor)
    return jsonify({
        'name': doctor.name,
        'token': token
    })

