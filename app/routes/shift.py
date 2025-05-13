from datetime import datetime
from flask import Blueprint, request, jsonify
from app.repositories.shift_repository import ShiftRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.shift import ShiftCreate
from app.schemas.payment import PaymentCreate
from app.database import db
from app.utils.auth import token_required

shift_bp = Blueprint('shift', __name__)
shift_repository = ShiftRepository()
payment_repository = PaymentRepository()

@shift_bp.route('/', methods=['POST'])
@token_required
def create_shift(current_user):
    data = request.get_json()
    shift_data = ShiftCreate(**data)
    shift = shift_repository.create(db.session, shift_data, current_user.id)
    payment_data = PaymentCreate(
        shift_id=shift.id,
        amount=shift.value
    )
    payment_repository.create(db.session, payment_data)
    return {'message': 'Criado com sucesso!'}

@shift_bp.route('/', methods=['GET'])
@token_required
def get_shifts(current_user):
    shifts = shift_repository.get_by_doctor(db.session, current_user.id)
    shifts_dict = [shift.to_dict() for shift in shifts]
    return jsonify(shifts_dict)

@shift_bp.route('/<int:shift_id>/complete', methods=['POST'])
@token_required
def complete_shift(current_user, shift_id):
    shift = shift_repository.get_by_id(db.session, shift_id)
    if not shift or shift.doctor_id != current_user.id:
        return jsonify({'message': 'Plantão não encontrado'}), 404

    shift = shift_repository.update_status(db.session, shift, "completed")
    
    return {'message': 'Atualizado com sucesso!'}

@shift_bp.route('/<int:shift_id>/cancelled', methods=['POST'])
@token_required
def cancelled_shift(current_user, shift_id):
    shift = shift_repository.get_by_id(db.session, shift_id)
    if not shift or shift.doctor_id != current_user.id:
        return jsonify({'message': 'Plantão não encontrado'}), 404

    shift = shift_repository.update_status(db.session, shift, "cancelled")
    
    return {'message': 'Atualizado com sucesso!'}

@shift_bp.route('/<int:shift_id>/paid', methods=['POST'])
@token_required
def paid_shift(current_user, shift_id):
    shift = shift_repository.get_by_id(db.session, shift_id)
    if not shift or shift.doctor_id != current_user.id:
        return jsonify({'message': 'Plantão não encontrado'}), 404
    
    shift_repository.update_status(db.session, shift, "paid")
    
    payment = payment_repository.get_by_shift(db.session, shift_id)
    payment_repository.update_status(db.session, payment, "paid")
    
    return {'message': 'Atualizado com sucesso!'}

@shift_bp.route('/dashboard', methods=['GET'])
@token_required
def get_dashboard(current_user):
    shifts = shift_repository.get_dashboard_stats(db.session, current_user.id)
    return jsonify(shifts)

@shift_bp.route('/financial', methods=['GET'])
@token_required
def get_financial(current_user):
    shifts = shift_repository.get_financial_chart_data(db.session, current_user.id)
    return jsonify(shifts)

@shift_bp.route('/financial/full', methods=['GET'])
@token_required
def get_financial_full(current_user):
    year = request.args.get('year', type=int)
    
    if year is None:
        year = datetime.now().year
        
    data = shift_repository.get_financial_data(db.session, current_user.id, year)
        
    return jsonify({
        "status": "success",
        "data": {
            "monthly_data": data["monthly_data"],
            "annual_totals": data["annual_totals"],
            "year": year
        }
    })
