from datetime import datetime
import uuid
from flask import Blueprint, request, jsonify, send_from_directory
from app.repositories.doctor_repository import DoctorRepository
from app.schemas.doctor import DoctorCreate, DoctorUpdate
from app.database import db
from app.utils.auth import token_required
import os
from werkzeug.utils import secure_filename

doctor_bp = Blueprint('doctor', __name__)
doctor_repository = DoctorRepository()

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@doctor_bp.route('/info/<int:doctor_id>', methods=['GET'])
def get_doctor(doctor_id):
    doctor = doctor_repository.get_by_id(db.session, doctor_id)
    if not doctor:
        return jsonify({'message': 'Médico não encontrado'}), 404
    return jsonify(doctor.to_dict(include_shifts_count=True))

@doctor_bp.route('/', methods=['POST'])
def create_doctor():
    data = request.get_json()
    doctor_data = DoctorCreate(**data)
    
    if doctor_repository.get_by_email(db.session, doctor_data.email):
        return jsonify({'message': 'Email já cadastrado'}), 400
    
    doctor_repository.create(db.session, doctor_data)
    return {'message': 'Criado com sucesso!'}

@doctor_bp.route('/me', methods=['GET'])
@token_required
def get_current_doctor(current_user):
    return jsonify(current_user.to_dict(include_shifts_count=True))

@doctor_bp.route('/me', methods=['PUT'])
@token_required
def update_doctor(current_user):
    data = request.get_json()
    update_data = DoctorUpdate(**data)
    
    doctor_repository.update(db.session, current_user, update_data)
    return {'message': 'Atualizado com sucesso!'}

@doctor_bp.route('/upload-photo', methods=['POST'])
def upload_photo():
    if 'photo' not in request.files or (file := request.files['photo']).filename == '':
        return jsonify({'error': 'Nenhum arquivo válido enviado'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext not in {'png', 'jpg', 'jpeg', 'gif', 'webp'}:
        return jsonify({'error': 'Tipo de arquivo não permitido'}), 400

    unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}.{ext}"
    safe_name = secure_filename(unique_name)
    file.save(os.path.join(UPLOAD_FOLDER, safe_name))
    
    return jsonify({'photo_url': f"{request.host_url}/static/uploads/{safe_name}"})