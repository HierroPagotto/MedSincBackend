from datetime import datetime as dt

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import db
from app.models.notification import (
    TYPE_APPLICATION_APPROVED,
    TYPE_APPLICATION_REJECTED,
    TYPE_GOAL_PROGRESS,
    TYPE_NEW_APPLICATION,
    TYPE_OPPORTUNITY_FILLED,
    TYPE_PAYMENT_PENDING,
    TYPE_SCHEDULE_CONFLICT,
    TYPE_SHIFT_TOMORROW,
)

EMAIL_FIELD_BY_TYPE = {
    TYPE_SHIFT_TOMORROW: "email_shift_tomorrow",
    TYPE_PAYMENT_PENDING: "email_payment_pending",
    TYPE_GOAL_PROGRESS: "email_goal_progress",
    TYPE_SCHEDULE_CONFLICT: "email_schedule_conflict",
    TYPE_APPLICATION_APPROVED: "email_application_approved",
    TYPE_APPLICATION_REJECTED: "email_application_rejected",
    TYPE_NEW_APPLICATION: "email_new_application",
    TYPE_OPPORTUNITY_FILLED: "email_opportunity_filled",
}

EDITABLE_FIELDS = ("email_enabled", *EMAIL_FIELD_BY_TYPE.values())


class NotificationPreference(db.Model):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True
    )

    email_enabled = Column(Boolean, nullable=False, default=True, server_default="1")
    email_shift_tomorrow = Column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    email_payment_pending = Column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    email_goal_progress = Column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    email_schedule_conflict = Column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    email_application_approved = Column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    email_application_rejected = Column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    email_new_application = Column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    email_opportunity_filled = Column(
        Boolean, nullable=False, default=True, server_default="1"
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")

    def allows_email(self, notification_type: str) -> bool:
        if not self.email_enabled:
            return False
        field = EMAIL_FIELD_BY_TYPE.get(notification_type)
        if not field:
            return True
        return bool(getattr(self, field, True))

    def to_dict(self):
        payload = {"user_id": self.user_id}
        for field in EDITABLE_FIELDS:
            payload[field] = bool(getattr(self, field))
        payload["updated_at"] = (
            self.updated_at.isoformat()
            if isinstance(self.updated_at, dt)
            else self.updated_at
        )
        return payload
