from flask import Blueprint, request, jsonify
import os

from app.database import db
from app.utils.auth import authenticated_user_required
from app.services.notification_service import notification_service

notifications_bp = Blueprint("notifications", __name__)
jobs_bp = Blueprint("jobs", __name__)


@notifications_bp.route("/", methods=["GET"])
@authenticated_user_required
def list_notifications(current_user):
    try:
        page = int(request.args.get("page") or 1)
        per_page = int(request.args.get("per_page") or 20)
    except ValueError:
        return jsonify({"message": "page/per_page inválidos"}), 400

    unread_only = request.args.get("unread_only", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    items, total = notification_service.list_for_user(
        db.session,
        current_user.id,
        page=page,
        per_page=per_page,
        unread_only=unread_only,
    )
    return jsonify(
        {
            "count": len(items),
            "total": total,
            "page": page,
            "per_page": per_page,
            "unread_count": notification_service.unread_count(
                db.session, current_user.id
            ),
            "notifications": [n.to_dict() for n in items],
        }
    )


@notifications_bp.route("/unread-count", methods=["GET"])
@authenticated_user_required
def unread_count(current_user):
    return jsonify(
        {"unread_count": notification_service.unread_count(db.session, current_user.id)}
    )


@notifications_bp.route("/<int:notification_id>/read", methods=["POST"])
@authenticated_user_required
def mark_read(current_user, notification_id):
    notification = notification_service.get_for_user(
        db.session, notification_id, current_user.id
    )
    if not notification:
        return jsonify({"message": "Notificação não encontrada"}), 404
    updated = notification_service.mark_read(db.session, notification)
    return jsonify(
        {"message": "Notificação marcada como lida", "notification": updated.to_dict()}
    )


@notifications_bp.route("/read-all", methods=["POST"])
@authenticated_user_required
def mark_all_read(current_user):
    updated = notification_service.mark_all_read(db.session, current_user.id)
    return jsonify({"message": "Notificações marcadas como lidas", "updated": updated})


@jobs_bp.route("/notifications/daily", methods=["POST"])
def run_daily_notifications_job():
    expected = os.environ.get("NOTIFICATIONS_JOB_SECRET") or ""
    provided = request.headers.get("X-Job-Secret") or ""
    if not expected or provided != expected:
        return jsonify({"message": "Não autorizado"}), 401

    result = notification_service.run_daily_job(db.session)
    return jsonify({"message": "Job de notificações executado", **result})
