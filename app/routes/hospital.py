from flask import Blueprint, request, jsonify
from app.repositories.hospital_repository import HospitalRepository
from app.schemas.hospital import HospitalCreate
from app.database import db
from app.utils.auth import token_required

hospital_bp = Blueprint('hospital', __name__)
hospital_repository = HospitalRepository()

@hospital_bp.route('/', methods=['GET'])
@token_required
def get_hospitals(current_user):
    hospitals = hospital_repository.get_all(db.session)
    if not isinstance(hospitals, list):
        return jsonify(hospitals.to_dict())
    return jsonify([hospital.to_dict() for hospital in hospitals])

@hospital_bp.route('/', methods=['POST'])
@token_required
def create_hospital(current_user):
    data = request.get_json()
    hospital_data = HospitalCreate(**data)
    hospital_repository.create(db.session, hospital_data)
    return {'message': 'Criado com sucesso!'}