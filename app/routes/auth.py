from app.utils.security import generate_token
from flask import Blueprint, request, jsonify
import bcrypt
from app.repositories.doctor_repository import DoctorRepository
from app.database import db
from app.utils.email import send_password_reset_email
import random
import string
from datetime import datetime, timedelta

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
        'token': token,
        'is_admin': doctor.is_admin
    })

@auth_bp.route('/password-reset/request', methods=['POST'])
def request_password_reset():
    data = request.get_json()
    email = data.get('email')
    
    doctor = doctor_repository.get_by_email(db.session, email)
    if not doctor:
        return jsonify({'message': 'Email não encontrado'}), 404
    
    code = ''.join(random.choices(string.digits, k=6))
    doctor.lost_pass_code = code
    doctor.lost_pass_code_requested_time = datetime.now()
    db.session.commit()
    
    send_password_reset_email(email, code, doctor.name)
    
    return jsonify({'message': 'Código de recuperação enviado para seu email'})

@auth_bp.route('/password-reset/verify', methods=['POST'])
def verify_password_reset_code():
    data = request.get_json()
    email = data.get('email')
    code = data.get('code')
    
    doctor = doctor_repository.get_by_email(db.session, email)
    if not doctor:
        return jsonify({'message': 'Email não encontrado'}), 404
    
    if not doctor.lost_pass_code or not doctor.lost_pass_code_requested_time:
        return jsonify({'message': 'Código não solicitado'}), 400
    
    if datetime.now() - doctor.lost_pass_code_requested_time > timedelta(hours=1):
        return jsonify({'message': 'Código expirado'}), 400
    
    if doctor.lost_pass_code != code:
        return jsonify({'message': 'Código inválido'}), 400
    
    return jsonify({'message': 'Código válido', 'valid': True})

@auth_bp.route('/password-reset/change', methods=['POST'])
def change_password():
    data = request.get_json()
    email = data.get('email')
    code = data.get('code')
    new_password = data.get('new_password')
    
    doctor = doctor_repository.get_by_email(db.session, email)
    if not doctor:
        return jsonify({'message': 'Email não encontrado'}), 404
    
    if not doctor.lost_pass_code or not doctor.lost_pass_code_requested_time:
        return jsonify({'message': 'Código não solicitado'}), 400
    
    if datetime.now() - doctor.lost_pass_code_requested_time > timedelta(hours=1):
        return jsonify({'message': 'Código expirado'}), 400
    
    if doctor.lost_pass_code != code:
        return jsonify({'message': 'Código inválido'}), 400
    
    hashed_password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
    doctor.password = hashed_password.decode()
    doctor.lost_pass_code = None
    doctor.lost_pass_code_requested_time = None
    db.session.commit()
    
    return jsonify({'message': 'Senha alterada com sucesso'})

