from flask import Blueprint, request, jsonify
from app.repositories.doctor_repository import DoctorRepository
from app.repositories.hospital_repository import HospitalRepository
from app.database import db
from app.utils.auth import token_required, admin_required
from app.models.shift import Shift
from app.models.payment import Payment

admin_bp = Blueprint('admin', __name__)
doctor_repository = DoctorRepository()
hospital_repository = HospitalRepository()

@admin_bp.route('/users', methods=['GET'])
@token_required
@admin_required
def list_users(current_user):
    doctors, count = doctor_repository.get_all(db.session)
    return jsonify({'count': count, 'users': [d.to_dict() for d in doctors]})

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_user(current_user, user_id):
    doctor = doctor_repository.get_by_id(db.session, user_id)
    if not doctor:
        return jsonify({'message': 'Usuário não encontrado'}), 404
    db.session.delete(doctor)
    db.session.commit()
    return jsonify({'message': 'Usuário deletado com sucesso'})

@admin_bp.route('/hospitals', methods=['GET'])
@token_required
@admin_required
def list_hospitals(current_user):
    hospitals = hospital_repository.get_all(db.session)
    return jsonify({'count': len(hospitals), 'hospitals': [h.to_dict() for h in hospitals]})

@admin_bp.route('/hospitals/<int:hospital_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_hospital(current_user, hospital_id):
    hospital = hospital_repository.get_by_id(db.session, hospital_id)
    if not hospital:
        return jsonify({'message': 'Hospital não encontrado'}), 404

    shifts = db.session.query(Shift).filter_by(hospital_id=hospital_id).all()
    for shift in shifts:
        payments = db.session.query(Payment).filter_by(shift_id=shift.id).all()
        for payment in payments:
            db.session.delete(payment)
        db.session.delete(shift)
    db.session.delete(hospital)
    db.session.commit()
    return jsonify({'message': 'Hospital, plantões e pagamentos associados deletados com sucesso'}) 
