from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError

from app.repositories.doctor_repository import DoctorRepository
from app.repositories.hospital_repository import HospitalRepository
from app.database import db
from app.utils.auth import token_required, admin_required
from app.models.shift import Shift
from app.models.payment import Payment

admin_bp = Blueprint("admin", __name__)
doctor_repository = DoctorRepository()
hospital_repository = HospitalRepository()


@admin_bp.route("/users", methods=["GET"])
@token_required
@admin_required
def list_users(current_user):
    doctors, count = doctor_repository.get_all(db.session)
    return jsonify({"count": count, "users": [d.to_dict() for d in doctors]})


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@token_required
@admin_required
def delete_user(current_user, user_id):
    from app.models.user import User
    from app.models.notification import Notification
    from app.models.notification_preference import NotificationPreference
    from app.models.opportunity_application import OpportunityApplication
    from app.models.financial_goal import FinancialGoal
    from app.models.doctor_specialty import DoctorSpecialty, DoctorPracticeArea

    doctor = doctor_repository.get_by_id(db.session, user_id)
    if not doctor:
        return jsonify({"message": "Usuário não encontrado"}), 404

    if current_user.id == doctor.id:
        return (
            jsonify({"message": "Você não pode deletar a própria conta por aqui"}),
            400,
        )

    linked_user_id = doctor.user_id

    try:
        # Vínculos do perfil (doctors.id)
        db.session.query(OpportunityApplication).filter_by(doctor_id=user_id).delete(
            synchronize_session=False
        )
        db.session.query(FinancialGoal).filter_by(user_id=user_id).delete(
            synchronize_session=False
        )
        db.session.query(DoctorSpecialty).filter_by(doctor_id=user_id).delete(
            synchronize_session=False
        )
        db.session.query(DoctorPracticeArea).filter_by(doctor_id=user_id).delete(
            synchronize_session=False
        )

        shift_ids = [
            row.id
            for row in db.session.query(Shift.id).filter_by(doctor_id=user_id).all()
        ]
        if shift_ids:
            from app.models.shift_expense import ShiftExpense

            db.session.query(ShiftExpense).filter(
                ShiftExpense.shift_id.in_(shift_ids)
            ).delete(synchronize_session=False)
            db.session.query(Payment).filter(Payment.shift_id.in_(shift_ids)).delete(
                synchronize_session=False
            )
            db.session.query(Shift).filter(Shift.id.in_(shift_ids)).delete(
                synchronize_session=False
            )

        from app.models.personal_expense import PersonalExpense

        db.session.query(PersonalExpense).filter_by(doctor_id=user_id).delete(
            synchronize_session=False
        )

        db.session.delete(doctor)
        db.session.flush()

        if linked_user_id:
            db.session.query(NotificationPreference).filter_by(
                user_id=linked_user_id
            ).delete(synchronize_session=False)
            db.session.query(Notification).filter_by(user_id=linked_user_id).delete(
                synchronize_session=False
            )
            user = db.session.query(User).filter(User.id == linked_user_id).first()
            if user:
                db.session.delete(user)

        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        detail = str(getattr(exc, "orig", None) or exc)
        return (
            jsonify(
                {
                    "message": "Não foi possível deletar: há registros vinculados a este usuário",
                    "detail": detail,
                }
            ),
            409,
        )
    except Exception:
        db.session.rollback()
        return jsonify({"message": "Erro ao deletar usuário"}), 500

    return jsonify(
        {"message": "Usuário, plantões e pagamentos associados deletados com sucesso"}
    )


@admin_bp.route("/hospitals", methods=["GET"])
@token_required
@admin_required
def list_hospitals(current_user):
    hospitals = hospital_repository.get_all(db.session)
    return jsonify(
        {"count": len(hospitals), "hospitals": [h.to_dict() for h in hospitals]}
    )


@admin_bp.route("/hospitals/<int:hospital_id>", methods=["DELETE"])
@token_required
@admin_required
def delete_hospital(current_user, hospital_id):
    hospital = hospital_repository.get_by_id(db.session, hospital_id)
    if not hospital:
        return jsonify({"message": "Hospital não encontrado"}), 404

    from app.models.hospital_staff import HospitalStaff
    from app.models.user import User
    from app.models.notification import Notification
    from app.models.shift_opportunity import ShiftOpportunity
    from app.models.opportunity_application import OpportunityApplication

    try:
        opportunities = (
            db.session.query(ShiftOpportunity).filter_by(hospital_id=hospital_id).all()
        )
        for opportunity in opportunities:
            db.session.query(OpportunityApplication).filter_by(
                opportunity_id=opportunity.id
            ).delete(synchronize_session=False)
            db.session.delete(opportunity)

        staff_members = (
            db.session.query(HospitalStaff).filter_by(hospital_id=hospital_id).all()
        )
        for member in staff_members:
            user = db.session.query(User).filter(User.id == member.user_id).first()
            db.session.delete(member)
            if user:
                db.session.query(Notification).filter_by(user_id=user.id).delete(
                    synchronize_session=False
                )
                db.session.delete(user)

        shifts = db.session.query(Shift).filter_by(hospital_id=hospital_id).all()
        from app.models.shift_expense import ShiftExpense

        for shift in shifts:
            db.session.query(ShiftExpense).filter_by(shift_id=shift.id).delete(
                synchronize_session=False
            )
            payments = db.session.query(Payment).filter_by(shift_id=shift.id).all()
            for payment in payments:
                db.session.delete(payment)
            db.session.delete(shift)
        db.session.delete(hospital)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return (
            jsonify(
                {
                    "message": "Não foi possível deletar: há registros vinculados a este hospital"
                }
            ),
            409,
        )
    except Exception:
        db.session.rollback()
        return jsonify({"message": "Erro ao deletar hospital"}), 500

    return jsonify(
        {"message": "Hospital, plantões e pagamentos associados deletados com sucesso"}
    )


@admin_bp.route("/hospitals/<int:hospital_id>/verify", methods=["POST"])
@token_required
@admin_required
def verify_hospital(current_user, hospital_id):
    hospital = hospital_repository.get_by_id(db.session, hospital_id)
    if not hospital:
        return jsonify({"message": "Hospital não encontrado"}), 404
    hospital.is_verified = True
    db.session.commit()
    return jsonify({"message": "Hospital verificado", "hospital": hospital.to_dict()})


@admin_bp.route("/hospitals/<int:hospital_id>/unverify", methods=["POST"])
@token_required
@admin_required
def unverify_hospital(current_user, hospital_id):
    hospital = hospital_repository.get_by_id(db.session, hospital_id)
    if not hospital:
        return jsonify({"message": "Hospital não encontrado"}), 404
    hospital.is_verified = False
    db.session.commit()
    return jsonify({"message": "Verificação removida", "hospital": hospital.to_dict()})


@admin_bp.route("/opportunities", methods=["GET"])
@token_required
@admin_required
def list_opportunities(current_user):
    from app.repositories.opportunity_repository import OpportunityRepository

    status = request.args.get("status")
    try:
        page = int(request.args.get("page") or 1)
        per_page = int(request.args.get("per_page") or 50)
    except ValueError:
        return jsonify({"message": "page/per_page inválidos"}), 400

    repo = OpportunityRepository()
    items, total = repo.list_all_admin(
        db.session, status=status, page=page, per_page=per_page
    )
    return jsonify(
        {
            "count": len(items),
            "total": total,
            "page": page,
            "per_page": per_page,
            "opportunities": [
                o.to_dict(include_hospital=True, include_applications_count=True)
                for o in items
            ],
        }
    )


@admin_bp.route("/opportunities/<int:opportunity_id>/cancel", methods=["POST"])
@token_required
@admin_required
def cancel_opportunity(current_user, opportunity_id):
    from app.repositories.opportunity_repository import OpportunityRepository
    from app.models.shift_opportunity import STATUS_CANCELLED

    repo = OpportunityRepository()
    opportunity = repo.get_by_id(db.session, opportunity_id)
    if not opportunity:
        return jsonify({"message": "Oportunidade não encontrada"}), 404
    if opportunity.status == STATUS_CANCELLED:
        return jsonify({"message": "Oportunidade já cancelada"}), 400
    cancelled = repo.cancel(db.session, opportunity)
    return jsonify(
        {
            "message": "Oportunidade cancelada pelo admin",
            "opportunity": cancelled.to_dict(include_hospital=True),
        }
    )
